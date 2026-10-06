# competitor 요청

## Storyboard 비교 기준으로 보내기 경로 안내 — storyboard · 2026-10-06
- 필요: 02-storyboard Q-3 · 경쟁사 CA5 `Storyboard 비교 기준으로` — competitor 는 storyboard 를 consumes 하지 않으므로 **웹이** 묶음을 옮긴다.
- 경로: `POST /api/storyboard/v1/storyboards/{sb_id}/imports/competitor {analysis_id, title, criteria: [{name, importance, source}], competitors: [..], note}`
  → `{question: PlanningQuestion | null, stored: true}` — SB1Q3 `비교 기준` 질의에 `경쟁사 제안` 선택지(근거 `비교 기준 a · b (경쟁사 A · …)`)를 더하거나 근거를 붙인다(익명으로 보낸다).
- 상태: 완료(안내 — storyboard 계약에 있음)
- 상태 갱신(competitor, 2026-10-07): CA5 웹이 `GET …/bundle?target=storyboard`(익명) → `POST /api/storyboard/v1/storyboards/{sb_id}/imports/competitor {analysis_id, title, criteria:[{name, importance(문자열), source}], competitors:["경쟁사 A" …], note}` 로 올리고 SB1Q3(`/storyboard/{sb}/planning/3`)으로 이동한다. 넘김 기록 `target=storyboard` · `delivered`. e2e `send.spec.ts` 로 요청 모양 확인.

## kb 요구 태그 문장 쓰기 — kb · 2026-10-07
- 필요: docs/requests/kb.md competitor 요청의 답. R01~R24 `label` 은 계속 null(KB 에 코드표 없음). `ca.make_criteria` 입력 · 실패 시 줄임 문장에
  `req_types[].examples_specific`(태그에 두드러진 요구 문장, 태그끼리 안 겹침)와 `hint_terms` 를 쓰면 같은 문장이 여러 태그 이름이 되는 일이 줄어든다. `pm2 restart kb` 뒤.
- 상태: 요청(kb → competitor 안내)

## 통합 세션 처리 — integration · 2026-10-07
- `hof_` 겹침(mi 넘김도 `hof_`): 완료 — proposal 이 작업 id 접두사(`ca_`)로 기능을 정한다(백엔드 `defs.feature_for_ref`, 웹 `handoffFeature`). CA5 → 제안서 why 섹션 반입이 mi 로 잘못 가지 않는다.
- CA5 「새 제안서로 시작」이 `TYPE_REQUIRED`(유형 없이 만들기)로 막히던 것: 완료 — 웹(`pages/SendPage.tsx`)이 넘김(`target_id: null`)을 만들고 `delivered` 로 표시한 뒤
  `/proposal/new?handoff=hof_…&link=ca_…&feature=competitor`(PR1 — 유형 고르기 → why 섹션에 넘김 반입)로 보낸다. `make typecheck` · `make e2e-feature SERVICE=competitor` 14 통과.
- 보충(integration · 2026-10-07): CA1R `?input=requirements&rq=` — 넘겨받은 정의서가 저장 목록 최근 50개 밖이면 첫 줄이 골라져 엉뚱한 정의서로 경쟁사를 찾던 것 → `savedDefinitions(preferred)` 가 따로 읽어 맨 앞에 둔다(`api.ts` · `pages/InputPage.tsx`). e2e 14 통과.
