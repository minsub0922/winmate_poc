# mi 요청

## Storyboard 읽기 · Key Message 근거 붙이기 경로 안내 — storyboard · 2026-10-06
- 필요: 03-mi E5 · MI1 `Storyboard 가져오기` · MI4 → SB2 `Key Message에 근거로 붙이기`. mi 는 storyboard 를 consumes 하지 않으므로 **웹이** 읽어 넘긴다(Q-2).
- 읽기: `GET /api/storyboard/v1/storyboards/{sb_id}` (`requirement_ref` · `direction.key_messages[]` · `outline.sections[]`), `GET …/{sb_id}/key-messages` → `{items: KeyMessage[]}`.
  SB4 카드는 `/mi/new?rq={rq_id}&sb={sb_id}` 로 보내고, 카드 설명(`{섹션 코드} 근거 — {찾을 것}`)은 `GET …/{sb_id}/handoffs` 의 `mi.description`.
- 근거 붙이기: `POST /api/storyboard/v1/storyboards/{sb_id}/key-messages/{kmsg_id}/evidence {source: {service: "mi", ref_id, title, route}, text, citations: [{title, url}]}`
  → 201 `KeyMessage`(evidence[] 에 더함). `kmsg_…` 는 Key Message id.
- 상태: 완료(안내 — storyboard 계약에 있음)
- mi 처리(2026-10-06): 반영함. MI1 `Storyboard 가져오기`(14일 안 SB 항목 카드 · `/mi/new?rq=&sb=`)는 웹이 `GET …/storyboards/{sb_id}` 를 읽어
  `POST /api/mi/v1/analyses/{id}/imports/storyboard` 로 올린다(요구사항 = `trace.items[].text`, Key Message = `direction.key_messages[].text`).
  MI4 `Key Message에 근거로 붙이기` 는 시트(Storyboard 고르기 → Key Message 라디오 → 근거 체크)에서 `POST …/key-messages/{kmsg}/evidence
  {source: {service: "mi", ref_id, title, route: "/mi/{id}/result"}, text, citations: [{title, url}]}` 를 근거마다 1번 부른다.
  근거 문장은 새 mi API `GET /v1/analyses/{id}/evidence`(storyboard 묶음과 같은 익명 · 대외비 규칙, `[00]` 수치 제외)에서 온다. 붙인 뒤 `Storyboard 에서 보기` → `/storyboard/{sb}/direction`.

## kb 업종 필드 쓰기(관측 대응 · 요구 태그 문장) — kb · 2026-10-07
- 필요: docs/requests/kb.md mi 요청의 답(맨 아래 `kb 답변`). `pm2 restart kb` 뒤.
  - `GET /v1/segments` 항목의 `mapping` · `mapping_basis`(seed · observed_cases · null) · `kr_vertical_ids_observed` · `case_basis` 로 6업종 근거를 표시하세요
    (SV · TP · VN · ID · OE = observed_cases, AD = 대응 없음). `kr_vertical_ids`(시드)와 업종별 사례 수 · classify 점수는 바뀌지 않았다.
  - R01~R24 `label` 은 계속 null(코드표 없음). 이름 대용은 `examples` 대신 `examples_specific`(태그별로 안 겹침) 첫 문장을 쓰고 `hint_terms` 를 보조로 — 둘 다 이름표가 아니라 `label_basis` 는 example 그대로.
- 상태: 요청(kb → mi 안내)

## 통합 세션 처리 — integration · 2026-10-07
- `hof_` 겹침(competitor 넘김도 `hof_`): 완료 — proposal 이 작업 id 접두사(`mi_`)로 기능을 정한다(백엔드 `defs.feature_for_ref`, 웹 `handoffFeature`).
- MI3V → 제품 사양 링크에 `from=mi:{analysis_id}`(spec 이 출처를 기록) — `pages/VerifyPage.tsx` · `api_more.py`.
- `GET /v1/analyses/{id}/design` 이 설계 잡 중간에 500(ResponseValidationError — `decide_competitors` 가 `competitors` 결정에 mode · reason 만 먼저 적음): 완료 —
  `service.design_view` 가 다 만든 결정 줄(key · label)만 보인다. `make test SERVICE=mi` 118 · `make e2e-feature SERVICE=mi` 10 통과.

## 허브 완료 화면 머리 = 보드 Done(짧은 이름) — storyboard · 2026-10-10
- 바뀐 것(허브 `/v1/flows*`, 응답 모양 그대로): `PUT /v1/flows/{id}/stages/{key}` 의 `md_added`(→ `push_stage` · 각 서비스 `flow_sync.md_added`) 첫 줄을
  보드 Done 머리(짧은 이름 · 번호 없음)로 바꿨다 — `## 요구사항 · RQ-06 v1` · `## DSS · …` · `## MI · MI-01 v2` · `## 경쟁사 · CA-01 v1` · `## VP · …` · `## Spec · …` · `## 시나리오 · …`.
  요약본 전체(`summary_md`)는 그대로 보드 SB1 형식(`## 1. 고객 요구사항 · RQ-01 v2` · `## 3. Market Intelligence · MI-01 v1`), 「남은 것」 줄의 시나리오는 `공간 시나리오`.
  함께: flow.json `progress` 는 보드 값 `rq` · `dss+n/5`(화면 문구 `FlowDoc.progress` 는 그대로), `keyPillars` 는 받쳐 줄 메시지가 있을 때만, 분기(`:branch`)는 Key message 를 복사하지 않는다(보드 SB0 · SBPopup).
- 맞출 곳: `services/mi/tests/test_mi_flow.py:166` `md_added.startswith(f"## Market Intelligence · {d['code']} v1\n- 시장 2 …")` → `## MI · {code} v1\n…`.
  (MI 가 보내는 md 첫 줄 `## Market Intelligence · …` 은 허브가 버리고 다시 붙이므로 `miflow.py:702` 는 그대로 둬도 된다.)
- 함께(이전 흐름): SB4 「다음에 할 일 · Market Intelligence」 카드 경로를 `/mi/new?rq=&sb=` → `/mi/legacy/new?rq=&sb=` 로 바꿨다(`/mi/new` 는 새 흐름 Gate). InputPage 가 `rq` · `sb` 를 그대로 읽는다.
- 상태: 완료(2026-10-10 플랫폼 통합 때 테스트 기대 문자열을 고침)
