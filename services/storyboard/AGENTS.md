# storyboard 서비스 — 개발 세션 규칙

전략 수립 Storyboard — 기획 질문 · 5단 목차 · 요구사항 추적 · 버전 비교 · 일정

- 포트: **5102** · 게이트웨이 경로: `/api/storyboard/v1/...` · 파이썬 모듈: `winmate_storyboard`
- 고칠 수 있는 경로(owns): `services/storyboard/**`, `web/src/features/storyboard/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`, `requirements`
- 화면 수용 기준: `docs/scenarios/02-storyboard.md` · 원본 보드: `docs/screens/` (INDEX.md)

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=storyboard          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=storyboard         # 이 서비스 테스트
make contracts SERVICE=storyboard    # contracts/storyboard.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("storyboard", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("storyboard")`(data/storyboard/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=storyboard` 를 돌리고 `contracts/storyboard.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태 (2026-10-10)

### 새 흐름 허브(2026-10-08 · 보드 정합 2026-10-10) — docs/scenarios/11-content-flow.md §6 · 보드 webapp1 SB0 · SB1 · SB1_Json · SB1_View · SB1_Strat · SB1_StratAI
- API `/v1/flows*`(본체 `flows.py`, 라우트 `api_flows.py`): 목록(`content=` → eligible · need · existing) · 만들기(internal, requirements) · 읽기 · 고침(이름 · Key message + 받쳐 줄 메시지 ≤ 3 · 요약본 사람 문장 `user_lines`) ·
  stage 넣기(internal — 같은 ref 의 다른 Storyboard 도 `synced`, 사전 작업 없으면 422 `PREREQUISITE_MISSING`) · `:branch`(사전 작업 사슬만 공유 · Key message 는 복사 안 함) ·
  `key-message:suggest`(`sb.key_message.v1` 3안, 근거 코드는 이 Storyboard 의 실제 코드로 · 없으면 규칙 후보) · `contents/{key}`(보드 List).
- 요약본 형식(보드 그대로): 전체 `summary_md` = SB1(`# 이름 — Storyboard 요약` · `고객: … · 최종 제안대상: … · main|분기 B` · `## Key message`(+ 받쳐 줄 메시지 `- …`) ·
  `## n. 고객 요구사항|DSS|Market Intelligence|경쟁사 분석|Value Proposition|Spec 시트|공간 시나리오 · REF vN` · `## 남은 것` `- 경쟁사 · VP · Spec · 공간 시나리오 → 제안서`).
  완료 화면 `md_added` = Done 머리(`## 요구사항|DSS|MI|경쟁사|VP|Spec|시나리오 · REF vN`, 번호 없음 — 콘텐츠가 보낸 첫 `## ` 줄은 버린다). 사람 문장은 그 절 끝에 `✎`(번호 머리 · 짧은 머리 둘 다 읽음).
  flow.json(`flow_json`) 키 순서 = SB1_Json(`keyPillars` 는 있을 때만), `progress` = `rq` · `dss+n/5`(화면 문구는 `FlowDoc.progress`).
- 웹 `flow/`: `FlowList`(SB0 `/storyboard` — 칸 1fr 480 · 300 · 120 · 110) · `FlowDetail`(SB1 `/storyboard/flow/:id` — 진행 8칸 · Key message · 연결된 콘텐츠 · 요약본 md / json 470 · 후속 작업 PPT ·
  분기 n 팝오버 → SBPopup · 보기 = 공용 ContentPopup · 만들기 = `/<base>/new?sb=&auto=1` · 요약본 수정(Esc 로 그만)) · `StrategyPopup`(1100×700 · AI 후보 360+1 점선 → 이 안 쓰기 → 저장) · `model.ts` · `sbf.css`.
  앱은 border-box 라 보드에서 content-box + 테두리인 칸은 테두리만큼 더했다(줄 51 · 머리 41 · 47 · 39 · 근거 칩 28 · 후보 361 · 63).
- 제안서 칸 비우기 · 콘텐츠 판(2026-10-10, 요청 proposal): `DELETE /v1/flows/{id}/stages/{key}?ref=`(internal · 지금은 `ppt` 만, 다른 키 422 `STAGE_NOT_CLEARABLE` ·
  ref 가 다르면 그대로 · 같은 ref 의 다른 Storyboard 도 비움) — proposal 이 제안서를 지울 때 부른다. `content_rev`(FlowDoc · 응답 · 색인 `meta.version`)는
  stage(ppt 칸 제외) · Key message · 받쳐 줄 메시지 · 요약본이 바뀔 때만 오른다 — 제안서가 ppt 칸에 자기를 적어도 「Storyboard 업데이트됨」이 뜨지 않게. 색인 `meta.customer` 도 있다.
- 테스트: pytest `test_flows.py` 11(ppt 칸 비우기 포함 · 보드 SB1 요약본 전문 일치 · Done 머리 7종 · 짧은 머리 사람 문장 포함). e2e `web/e2e/storyboard/sb-flow.spec.ts`(API 로 SB-01 모양 + MI 분기 → SB0 → SB1 → 보기 → json → 전략 수립 → AI 3안 → 수락 · 저장 →
  요약본 수정 ✎ → 경쟁사 저장 뒤에도 유지 → VP 만들기(Gate 건너뜀) → 분기 n → SBPopup → 분기 SB1), 캡처 `__screens__/SB0-new` · `SB1-new` · `SB1_View-new` · `SB1_Json-new` · `SB1_Strat-new` · `SB1_StratAI-new` 외.
- 보드와 다름: 요약본 Key message 절에 받쳐 줄 메시지 줄을 함께 쓴다(보드 SB1 예시엔 한 줄 메시지만 — PPT 가 요약본을 읽으므로) · json 탭 줄 나눔은 패널 폭(≈60칸)에 맞춘 자동 나눔(보드는 손으로 2줄) ·
  Key message 가 없을 때 점선 카드 「아직 없음 · …」(보드에 없는 상태) · 분기 Storyboard 머리에 부모 칩(「SB-01 · MI에서 분기」) · 렌더 글꼴 줄 높이 차이로 세로 1~3px.
- 이전 흐름 링크: SB1 「정의서가 없어요」 → `/requirements/legacy/new?return=storyboard` · SB4 MI · 공간 시나리오 카드 → `/mi/legacy/new?rq=&sb=` · `/scenario/legacy/new?sb=`(`/<base>/new` 는 새 흐름). 이전 e2e `list-sync` 는 `/storyboard/legacy`.

### API — `/v1` 44 경로(`contracts/storyboard.json`), 오류는 한국어 `{error:{code,message,details}}`
- 목록 · 만들기: `GET /storyboards`(tab · q · customer · updated_after · cursor 20, 시작 전 초안 제외) · `GET /storyboards/counts` ·
  `POST /storyboards`(201 새로, 내 시작 전 초안이 있으면 200 재사용, 7일 지난 초안 정리, 버전 0 정의서 422 `RQ_NOT_SAVED`) · `GET|PATCH /storyboards/{sb}`(name · step)
- 1 불러오기: `PUT requirement`(step ≥ 2 → 409 `STAGE_LOCKED`) · `POST prepare` · `PATCH settings` · `GET planning` · `PUT planning/{pq}`(순서 · 역할 · 직접 입력 · 꼬리 답, 빈 답 422 `NOTHING_SELECTED`)
- 2 기획 방향: `POST|GET|PATCH direction`(skip_planning → 모두 unknown) · `GET key-messages` · `PATCH key-messages/{kmsg}`(VP 되돌려 쓰기 `source`) ·
  `POST key-messages/{kmsg}/flags/{flg}/apply|revert` · `POST key-messages/{kmsg}/evidence`(MI4) · `POST imports/competitor`(Q-3)
- 3 목차: `POST|GET outline`(retry) · `GET spaces/{spc}` · `POST spaces/{spc}/questions`(200 있음 · 202 잡) · `PUT spaces/{spc}/slots/{slot}`(unknown → 정의서 고객 질문, 멱등) ·
  `POST spaces/{spc}/compose` · `POST discussions/agenda` · `POST revisions` · `GET revisions/{rev}` · `POST revisions/{rev}/apply|discard`(409 `REVISION_STALE`) ·
  `POST save`(201 · 바뀐 것 없으면 200 created=false) · `GET versions` · `GET versions/{n}` · `POST versions/{n}/restore` · `GET compare` · `POST changes/{chg}/revert` ·
  `POST requirement-sync`(dry_run → `sync-previews/{syp}`) · `GET sync-previews/{syp}`
- 4–5: `GET trace` · `PUT trace/items/{rq_item}/resolution`(exclude 사유 없으면 422 `REASON_REQUIRED`) · `POST trace/extensions/acknowledge` · `GET schedule` ·
  `POST exports`(잡 `sb.export` → export 서비스, 작업본 ≠ 최신 버전이면 먼저 저장) · `POST share` · `POST review-requests` · `GET handoffs` · `POST handoffs/{target}` ·
  `GET proposal-handoff`(10-proposal §8.0 ProposalHandoff v1)
- 읽을 때 자동 동기화: 정의서 링크 `pending` 이면 `sb.rq_sync` 시작, 반영 요청 없는 새 버전은 `rq_update`(SB3 띠). requirements 확인은 20초에 한 번.

### 워크플로(LangGraph · `worker.py` HANDLERS)
- `sb.prepare` 설정 4 · 질의 ≤ 3 · `sb.direction` 축 3 + 조합 · 메시지 · 표현 검사 · `sb.messages` · `sb.outline`(classify → map_axes → write_sections → trace, `step` 이벤트 · 섹션마다 부분 저장) ·
  `sb.space.questions` · `sb.space.compose` · `sb.revise` · `sb.rq_sync`(dry-run · 반영) · `sb.trace.apply` · `sb.trace.refresh` · `sb.export`
- 결정적 가드: 숫자(입력에 없는 수치 → `[00]`) · 주장(최초 · 유일 · 1위 …) · 내부 목표(제작자 의견 구절 + 스펙인 · 수주 · 매출 목표 → 내부 메모, 되돌리기 가능) ·
  수정 때 자리표시 보존(줄 단위) · 추적 완전성(항목마다 한 번, 버리지 않음) · 확장은 정의서에 쓰지 않음
- 모델: `ai().json(..., confidential=True)` 만, task `sb.<동작>`(자리별 `sb.section.<key>` · `sb.slot_questions.<공간>` · `sb.slot_compose.<공간>` · `sb.revise.<key>`).
  403 `POLICY_CONFIDENTIAL` · 503 · 504 는 한국어 오류로. 출력은 id 대신 요구 코드(RQ-01) · 자리 키(overview · p1_2 · `space:lobby`)로 받아 결정적으로 맞춘다.
- mock 시연 속도: `MODEL_MODE=mock` 이면 단계마다 0.45초(`SB_PACE_S`, 0 = 끔 — 테스트는 0). SB3G · 스켈레톤이 보이게 하려는 것.

### 웹(`web/src/features/storyboard`) — 25 화면
- `/storyboard` SB0 · `new` SB1(만들기 → `:sb/source`) · `:sb`(지금 화면으로) · `:sb/source` SB1 · `settings` SB1S · `planning/:i` SB1Q~Q3 · `direction` SB2 ·
  `direction/messages` SB2E · `outline` SB3G/SB3(부분 보기 `?view=partial`) · `outline/part2` SB3P · `outline/all` SB3D · `spaces/:spc/q` SB3S · `spaces/:spc/done` SB3S2 ·
  `revise` SB3R · `revise/:rev` SB3R2 · `versions` SB3V(미리 보기 `?preview_rq=&reply=`) · `trace` SB4T · `trace/resolve/:i` SB4U · `trace/resolved` SB4U2 ·
  `trace/all` SB4TD · `trace/extensions` SB4X · `schedule` SB5 · `saved` SB4 · `export` SB4E
- 파일: `lib.ts`(타입 · `sbApi` · `useSb` · `useJobRefresh`(SSE) · 문구 · 조사) · `parts.tsx`(화면 틀 · 하단 줄 · 선택 카드 · 분할 버튼 · 배지 · 자리표시) · `Stage*.tsx` · `sb.css`(토큰만)
- 키트에 없는 것(브랜드 분할 버튼 · 선택 카드 · Q 상자)은 지역 부품 — `docs/requests/workspace.md` 에 요청.

### 테스트
- pytest 42개(`make test SERVICE=storyboard`): 9.1 수용 기준 1–34 + 실제 requirements 앱 통합 · 실제 export/files PPTX · PDF 렌더.
  requirements 가짜(`tests/sb_rqdata.py`)는 계약에서 빠진 필수 값을 채워(`conform_response`) 계약이 자라도 엄격 검증을 통과한다.
- e2e(`make e2e-feature SERVICE=storyboard`): `flow.spec.ts`(9.2 2–15, 12개) · `list-sync.spec.ts`(9.2 1 · 16) — 정의서는 requirements API 로 만든다.
  storyboard · requirements 가 게이트웨이에서 안 보이면 이유를 남기고 건너뛴다. 화면 캡처 `web/e2e/storyboard/__screens__/SB*.png`(25장).
  설치된 Chromium 판이 달라 `suggestedFilename()` 이 `download` 로 오면 Content-Disposition 으로 파일 이름을 확인한다.
- mock 고정 응답 `mocks/ai-tools/sb.*.json` 40개(보드 예시: E 자산운용 용산 AI Ready 오피스 · 공간 7 · 요구 12).

### 문서 · 보드와 다르게 정한 것
- 수정 요청 가드 4(자리표시 보존)는 줄 단위라 SB3R2 보드 예(`출처 확인 전까지 각주로`)와 달리 바뀐 줄에 원래 `[00]` · `[확인 필요]` 가 남는다(9.1-20 우선).
- 바뀐 곳 수는 SB3R2 · SB3V 모두 유지 제외(Q-1). 정리 결과 `보류`(회색) · `제외`(점선) 배지 추가(Q-14).
- 분량 힌트 · 근거는 공간 수 규칙: 정의서 맥락의 공간, 없으면 정의서 내용으로 고른 업종의 KB 공간(둘 다 source=rq).
- 섹션 `확인 필요` 는 정의서에서 확인 필요인 항목이 `직접` 연결된 섹션에만 번진다. 제목은 `{고객사} {짧은 이름} 제안 기획`(정의서 제목이 고객사로 시작하면 한 번만).
- 내보내기 언어(영문 · 병기)는 설정만 넘기고 번역하지 않는다(Q-16 미정). 내부 검토 요청은 검토자를 안 주면 workspace 의 다른 사용자 한 명.
- `회의 안건에 넣기` = 안건 글 클립보드 복사(Q-8), SB3D `공유` = 공유 링크 복사, SB3 `추가 논의 {n}` → SB3D 추가 논의 줄.
- 다른 기능 넘기기는 웹 이동 + 기록(`POST handoffs/{target}`): `/proposal/new?sb=&rq=` · `/mi/legacy/new?rq=&sb=` · `/scenario/legacy/new?sb=`(2026-10-10 — `/<base>/new` 는 새 흐름 Gate). mi · scenario · competitor 는
  storyboard 를 consumes 하지 않아 웹이 읽어 넘긴다(Q-2 · Q-3, 안내는 `docs/requests/{mi,scenario,competitor,vp,proposal}.md`).

### 알려진 빈 곳
- 일정 편집(Q-5) · 섹션 상태 수동 변경(Q-13) · TopBar 팝오버 추가(Q-15)는 문서 기본값대로 없음. SB1 정의서가 5개를 넘을 때 `다른 정의서 찾기` 없음.
- e2e 는 공유 작업 트리의 다른 세션이 공용 파일을 바꾸면(Vite 다시 읽기) 흔들릴 수 있어 묶음을 한 번 더 시도한다.

### 통합(integration · 2026-10-07)
- 정의서 새 버전 띠 `rq_update.note` 를 채운다 — 지금 쓰는 버전 뒤 저장된 버전들의 변경 수 합 · 최근 저장 메모(`GET /v1/requirements/{id}/versions`, `rq.update_note`). 「요구사항 정의서 v2이 새로 저장됐어요 · 변경 1건 · 회의 반영」. 테스트 스텁에 `/versions` 추가(pytest 42).
