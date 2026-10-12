# requirements 서비스 — 개발 세션 규칙

고객 요구사항 — 입력 폼 · 파일로 채우기 · 심층 작성 · 고객 질문 · 정의서 버전

- 포트: **5101** · 게이트웨이 경로: `/api/requirements/v1/...` · 파이썬 모듈: `winmate_requirements`
- 고칠 수 있는 경로(owns): `services/requirements/**`, `web/src/features/requirements/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`
- 화면 수용 기준: `docs/scenarios/01-requirements.md` · 원본 보드: `docs/screens/` (INDEX.md)

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=requirements          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=requirements         # 이 서비스 테스트
make contracts SERVICE=requirements    # contracts/requirements.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("requirements", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("requirements")`(data/requirements/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=requirements` 를 돌리고 `contracts/requirements.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태 (2026-10-12)

### 새 흐름 — 보드 webapp1 v63 RQ0 · RQ1 · RQ_Draft · RQ1_Edit · RQ_View · 본문 RQBody(2026-10-12) · `docs/scenarios/11-content-flow.md` §6 · `docs/handoff/2026-10-12-content-detail-v63.md`
- **상세는 최종본 한 장**(v63): 완료 화면(RQ_Done · FlowDoneView) · RQ1 자체 푸터 · 스텝바는 없앴다. 작성 중 · 저장됨 · 고치는 중이 같은 화면이고, 저장하면 그 자리에서 저장됨으로 바뀐다.
- **AI 심층 질의(폼 개선 과정)는 2026-10-12 에 뺐다** — 사용자 결정. `deep-questions` 경로 · `RFDeep*` 스키마 · `rq.deep_questions.v1` · 웹 DeepPanel 없음.
  예전 문서에 남은 `deep` · `target_ask` 칸은 읽을 때 버리고(`_DROPPED`), 출처 `by` 의 `ai-pending | ai-accepted` 는 예전 값 읽기용으로만 남겼다.
- **API** `/v1/rq-flows*`(rqflow.py · api_flow.py, 스키마 `RF*`, DocStore `rq_flows`, id `rqf_…`, 코드 `RQ-NN` — 허브 rq ref 최대값 다음 번호):
  만들기 · 목록 · 읽기(id 또는 코드) · `PUT` 폼 전체(`expected_version` 409, 채우는 중 409 FILLING) · `:fill` 202(잡 `rq.flow.fill`, 빈 칸만 · 사람 값 보호 · 숫자 가드) ·
  `:finish`(처음 = `create_flow` 로 Storyboard 자동 생성 · 다음 = `push_stage("rq")`, ver = 저장 횟수, 제작자 의견은 stage · 요약 · 카드에서 빠짐) ·
  `DELETE /v1/rq-flows/{id}`(저장 전 초안만 204 — 저장한 것은 409 `SAVED_CONTENT`, `?expected_version=` 이 다르면 409 VERSION_CONFLICT, 없으면 404 · 채우는 잡 취소 · 번호 다시 안 씀).
- **고친 곳 · 되돌리기(v63)**: `:finish` 가 사람이 고치는 값 `EDIT_KEYS`(title · customer · target · note · keymen · *_by)를 판으로 남긴다(`winmate_common.edits`, 문서 `saved_snapshot` — 응답에는 안 실음).
  `RFDoc.changes` = 저장한 판과 지금 값의 다른 곳 수(저장 전 0) — 칸 하나 = 1(프로젝트명 · 고객사 · 최종 제안대상 · 제작자 의견 · 키맨 이름 · 가중치 · 요구 문장 · 확인 필요),
  키맨 · 요구는 id 로 맞춰 앞에 끼워도 1, 빈 키맨 자리는 세지 않음. stage(…) 는 요구 문장이 needs · goals · requirements 에 겹쳐 한 번 고쳐도 여러 번 세므로 쓰지 않고 `_edit_view` 로 센다.
  `POST /v1/rq-flows/{id}:revert` → 저장한 판으로 되돌린 문서(changes 0 · ver · 연결 그대로), 저장한 적 없으면 409 `NOT_SAVED`(「아직 저장하지 않아 되돌릴 판이 없어요」), 채우는 중 409 FILLING.
  예전에 저장해 판이 없는 문서는 읽을 때(`load_api`) · 고치기 · 채우기 · 되돌리기 전에 지금 값을 판으로 남긴다(`ensure_snapshot`, 한 번 다시 씀).
- **웹** `web/src/features/requirements/flow/`: `/requirements`(RQ0 = `ContentListScreen content="rq"`, 작성 중 = rq-flows 중 내용 있는 초안 — 저장 전 초안 카드 × → `useRfDelete`) ·
  `/requirements/new`(RQ1 — 팝업 없이 바로 빈 최종본, 처음 내용이 들어간 칸을 떠날 때 초안을 만들고 주소를 `/requirements/flow/:id` 로 replace · 들어오기만 해선 안 만듦 · 이번에 만든 것은 저장 전까지 「새로 만들기」, 다시 열면 「작성 중」) ·
  `/requirements/flow/:id`(상세 = 공용 `ContentDetail` + `RqBody`). 본문은 보드 RQBody px 그대로(`rqflow.css` 접두어 `rqb-`): 파일 띠(새로 60 점선 · 나머지 46) · 그리드 `340px | 1fr`(간격 14) ·
  개요(입력 38 · 제작자 의견 남은 높이 · 「모두 선택 항목이에요 · 비어 있어도 저장돼요」) · 키맨별 요구사항(머리 50 · 「키맨 n · 요구 m · 가중치 합 x%」 100 아니면 노랑 · 키맨 카드 `176px | 1fr` · 요구 줄 n · 칸 32 · 확인 필요 · ×).
  칸은 공용 `InlineInput`(떠날 때 · Enter 에 저장 → 폼 전체 PUT · 60ms 안의 고침은 묶음). 가중치는 칸마다 따로(다른 키맨 값을 바꾸지 않음 — 저장 때 서버가 합 100 으로 맞춤).
  저장된 것을 이 화면에서 고친 칸은 `cd-in--chg` + 「고침」/「새로 씀」(기준 = 연 때 · 저장 · 되돌리기 한 때의 폼, 화면 상태). 저장 = `:finish`(토스트에 Storyboard 만듦 · 반영), 되돌리기 = `:revert`.
  후속 작업(저장된 것만): 그 Storyboard 에 DSS 가 있으면 「DSS-nn vN · 열기」(허브 cell route), 없으면 `/dss/new?sb=<id>&auto=1`. 보드에 없는 것: 키맨 빼기(카드 오른쪽 위 ×) · 요구 줄 「확인 필요로 표시」(손을 올리면) · Enter 새 줄 · 빈 줄 Backspace 빼기.
- **이전 흐름 이동**: 목록 · 새로 만들기만 `/requirements/legacy` · `/requirements/legacy/new`. 나머지 `/requirements/:rqId/...` 는 그대로(제안서 handoff).
- **테스트** `test_requirements_flow.py` 10개(전체 42 — 고친 곳 · 되돌리기 · 판 없는 예전 문서 포함) · e2e `rq-flow.spec.ts` 4개(목록 → 빈 최종본 → 입력 → 저장 → 저장됨 → 고친 곳 1 → 되돌리기 → v2 ·
  파일 빈 칸만 · 작성 중 · 빈 폼 · 1920 · 폭 340 · 746 · 176 · 1100 · 1180, 높이 보드 좌표 그대로) · `rq-draft.spec.ts` 1개 · 캡처 `__screens__/RQ1 · RQ_Draft · RQ_View · RQ1_Edit · RQ0-draft-delete.png`.

### 이전 흐름(`/v1/requirements*`, 2026-10-06)

**문서와 다른 점(소비자 먼저 볼 것)**
- 정의서 내용은 `GET /v1/requirements/{id}?version=` 이 아니라 저장 스냅숏 `GET /v1/requirements/{id}/versions/{n|latest}` 로 읽는다.
  스냅숏: `form`(제작자 의견 `author_note` 는 **internal**) · `context`(vertical · spaces · products · solutions …) · `keymen` ·
  `items_flat[]`(id · code · text · short · keyman_id/name/weight · needs_confirmation · evidence · entities · `source`(file_id · locator · quote)) ·
  `customer_questions` · `source_files`. 응답 맨 위에 title · customer_name · project_name · final_audience · item/keyman/open_question 수 · `latest_version`.
- 링크 경로 변수 이름은 `{service_name}`(URL 은 문서와 같음 `PUT|DELETE /v1/requirements/{id}/links/{service}/{ref_id}`, internal).
- 고객 질문 `origin.kind` 에 `proposal` · `reply` 추가. 입력은 `origin.feature`(SB → storyboard, PR → proposal)만 줘도 된다. 같은 `ref_id` + `text` 는 멱등(200).
- 추가 경로: `POST /v1/requirements/from-files`(제안서 R3) · `POST …/files/{file_id}/restore`(빼기 되돌리기) · `POST …/deep-sessions/{sid}/reanalyze` ·
  `GET …/versions/latest` · `POST|GET …/exports`(DOCX/PDF, 제작자 의견 제외). 세션 상태에 `failed`(분석 잡 실패) 추가.
- 응답 스키마는 기본값 있는 필드도 required(`json_schema_serialization_defaults_required`) — 생성 TS 타입이 optional 이 아니다.
- `Requirement` 응답에 화면용 필드 추가: `fill_progress`(새로고침 복구) · `active_deep{session_id,status,current_index,total}` · `last_deep_session_id` · `skipped_ops`.
- 저장 위치: 고객 질문은 정의서 문서 안, 세션 · 버전 · 답변 · 링크 · 내보내기는 각 컬렉션. 작업물 색인(register_item)은 내용이 바뀔 때만(`indexcache`).
- 모델 task 를 문서 종류 · 제안 종류로 나눴다(`rq.extract_rfp|memo|mail|other`, `rq.rewrite_item|add`) — 정적 mock 이 결정적이도록.

**API** — `contracts/requirements.json` 33 경로: 정의서(만들기 · 목록 `tab q has_version customer project_id owner cursor` · counts · 읽기 ·
`PATCH draft` ops 10종 · save · share · from-files), 파일(채우기 202 · 빼기 rollback · 되돌리기), 버전(목록 · n|latest · restore · diff),
심층 작성(만들기 202 · 읽기 · 고르기 · 취소 · 다시 분석 · start · answers · accept · revise · finish), 고객 질문(목록 · 추가 · 고치기 · mail-draft),
답변(만들기 202 · 읽기 · 고르기 · apply), 링크(목록 · PUT/DELETE internal), 내보내기. 오류 코드는 §6.10 전부(한국어 메시지).

**잡 · 그래프**(`worker.py` HANDLERS, `run_graph`)
- `rq.fill` — rq_fill: load_files → parse_blocks(메일 본문 · 첨부, 그림 쪽 `rq.i2t_page`) → classify_doc → plan_slots → extract_merge(칸마다 저장 + progress,
  사람 값 보호 → alternatives, 파일 우선순위 rfp > mail > memo) → kb_link(A1 · A2 · 공간/제품/솔루션) → short_texts → finalize. 같은 정의서 잡은 차례로(queued_jobs).
- `rq.deep.analyze` — rq_deep_analyze: snapshot → rule_gaps → kb_context → kb_gaps(B2) → llm_gaps(`rq.gaps`) → rank_and_cap(≤7, KB ≤2) → make_questions → score → save.
- 답 하나는 동기 그래프 rq_deep_answer(API 프로세스, 30초): 값 바로 반영 / 문장 제안(`rq.rewrite_item|add`, 숫자 가드 1회 재시도) / 모름(`rq.customer_question`, 실패 · 엉뚱하면 종류별 템플릿) / 건너뛰기.
- `rq.reply.analyze` — load → match_questions(`rq.reply_match`) → detect_changes(`rq.reply_changes`) → validate_ops(대상 확인 · 숫자 가드 · **답변 · 첨부에 근거 없는 변경 버림**) → impact(Storyboard 위치) → save.
- `rq.short`(항목 short · 제목, 30초에 한 번) · `rq.export` · `noop`. 메일 문구는 동기(15초 넘거나 내부 말이 섞이면 템플릿).
- 모든 모델 호출 `confidential=True`, 403 POLICY_CONFIDENTIAL · 503 LLM_UNAVAILABLE · 504 LLM_TIMEOUT 은 문서 문구로. 폼 입력 · 저장은 모델 없이 된다.
- mock 고정 응답 `mocks/ai-tools/rq.*.json`(보드 예시: E 자산운용 용산 AI Ready 오피스). 다른 입력에선 글 대조 · 관련성 · 숫자 가드로 걸러 템플릿/원문으로 내려간다.
- 선택 설정 `RQ_FILL_SLOT_DELAY_MS`(기본 150, 칸 사이 간격 — RQ1G 처럼 차례로 채워 보임. 테스트는 0).

**웹** — `web/src/features/requirements/`: `/requirements/legacy`(RQ0) · `/legacy/new` · `/:rqId/form`(RQ1 · RQ1D · RQ1G · RQ2) · `/:rqId/deep/:sid`(RQ3) ·
`/:rqId/deep/:sid/q`(RQ3A · RQ3B) · `/:rqId/deep/:sid/result`(RQ3C) · `/:rqId/saved`(RQ4) · `/:rqId/questions`(RQ5) · `/:rqId`(RQ6, `?v=`) ·
`/:rqId/reply`(RQ7) · `/:rqId/reply/:replyId`(RQ7B). 자동 저장 800ms(ops 큐 · 409 다시 적용), 잡 진행 SSE(`useJob`, 새로고침 복구),
RQ7B 저장 뒤 `pending_sync_links` 마다 storyboard `requirement-sync` 호출(기다리지 않음). 키맨 색은 토큰이 없어 `rq.css` 지역 변수(workspace 요청).
RQ1 입력형 카드는 카드 안에 포커스가 있는 동안 목록형으로 바뀌지 않는다(타이핑 중 레이아웃 튐 방지). 항목 끌어 옮기기(`move_item`)는 API만.

**테스트** — `make test SERVICE=requirements` 이전 흐름 32개(API · 저장소 · 그래프 · 오류 · 플랫폼 실제 앱 in-process; §9.1 AC 1~34) ·
`make e2e-feature SERVICE=requirements` 11개(`flow.spec.ts` 기본 흐름 E2E 2 · 6~13, `branches.spec.ts` E2E 1 · 3 · 4 · 5 · 14 · 15 · 16,
`weights.spec.ts` 가중치 규칙 웹 단위). 화면 캡처 `web/e2e/requirements/__screens__/`. e2e 는 `make dev-bg SERVICE=requirements` 를 띄운 뒤.

**알려진 한계** — 내보내기는 API 만(화면 버튼 없음, §11 Q-6) · 공유는 workspace 공유 링크 · 팝오버 "현재 작업에 추가"는 받지 않음(§11 Q-12).
