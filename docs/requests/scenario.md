# scenario 요청

## Storyboard Part 2 → 공간 시나리오 넘기기 경로 안내 — storyboard · 2026-10-06
- 필요: SB4 `공간 시나리오` 카드(`Part 2의 {n}개 공간을 시트로 — {완성 공간}는 5칸 그대로`) → `/scenario/new?sb={sb_id}`.
- 읽기(웹, scenario 는 storyboard 를 consumes 하지 않음 — Q-2): `GET /api/storyboard/v1/storyboards/{sb_id}` 의 `outline.spaces[]`
  = `{id: spc_…, key, name, purpose, is_extension, status(empty|draft|supplemented), slots: {action|trigger|response|exception|metric: {state, segments: [{text, ai_added}]}}, products: [{name, is_extension, kb_ref}]}`.
  `ai_added=true` 구간은 고객 확인 전(점선 표시), `[00]` · `[확인 필요]` 는 추정하지 않은 자리표시다.
- 상태: 완료(안내 — storyboard 계약에 있음)

## 이미지 렌더 API · 장면 이미지 요청 경로 안내 — image · 2026-10-06
- 안내(계약 `contracts/image.json`, 07-image §6.8 · §6.9 — scenario 가 image 를 consumes 해야 한다):
  - 렌더(화면 없음, T2I 를 직접 부르지 않는다): `POST /v1/renders {origin: {service: 'scenario', ref}, kind: 'scene', prompt: {subject_ko, details_ko[], negatives[]},
    aspect, target: 'fhd'|'uhd', structure_ref_file_id?, edit_of?: {file_id, instruction}, reference_file_ids[], product_refs: [{model_code|family_id, qty}],
    expect?: {products: [{model_code, qty, bbox_hint?}]}, forbid: ['competitor_logo','real_person_face','gibberish_text'], allow_people: 'none'|'silhouette'|'generic',
    confidential, label?}`(internal) → `202 {job_id, render_id}`. 진행은 jobs SSE(job_id), 결과 `GET /v1/renders/{id}` → `{status, image_id, version_id,
    renditions: [{kind, w, h, file_id, url, method}], generation, qc}`. 취소 `POST /v1/renders/{id}:cancel`. 렌더 결과는 IMG0 갤러리에 나오지 않는다.
  - 사람이 IMG 화면에서 만들게 하려면(SC4E 「이미지 생성에서 다시 만들기」): `POST /v1/requests {from_service: 'scenario', from_ref: <장면 ref>, from_label:
    "공간 시나리오 · A 커피 매장 하루", title: "장면 2 · 점심 피크 주문", prefill: {kind: 'scenario', description, products: ['QM55C' | {model_code, qty}], aspect, space_label}}`
    (internal, 사용자 헤더 전달) → IMG0 「다른 기능에서 요청한 이미지」. 바로 열려면 웹 `/image/new?request=irq_…`(IMG1) — `:start` 응답의
    `conditions_route`(IMG2)로 가도 된다. 결과는 `GET /v1/requests?from_service=scenario&from_ref=…` 의 `status=fulfilled` · `result_version_id`
    (IMG4 「공간 시나리오 장면으로」가 채우고 웹은 `/scenario?image_version=imv_…&request=irq_…` 로 보낸다), 버전 내용은 `GET /v1/versions/{id}`.
  - 장면에 쓰면 `POST /v1/images/{image_id}/usages {version_id, service: 'scenario', ref, label}`(internal), 빼면 `DELETE /v1/images/{id}/usages/scenario/{ref}`.
- 상태: 완료(안내 — image 계약에 있음)

## 상태 갱신(scenario · 2026-10-07)
- Storyboard Part 2 → 공간 시나리오: 반영 — SB4 `/scenario/new?sb={sb_id}` → SC1 이 `POST /v1/scenarios {storyboard_id}` 로 만들고, 서버가 `GET /v1/storyboards/{sb_id}`
  (consumes 에 storyboard 추가됨)의 `customer_name` · `outline.spaces[]` 로 고객 · 「[공간] {name} — {purpose}」 입력 줄 · 공간 라벨을 미리 채운다. SC2 사이드바에서
  Storyboard 를 끌어오면(`POST /v1/scenarios/{id}/imports {feature:'SB', ref}`) 같은 줄을 붙인다. 읽기 실패면 빈 값(화면은 멈추지 않음).
- 이미지 렌더 API · 장면 이미지 요청: 반영 — SC4 「이미지 생성」 = `POST /v1/requests`(prefill kind 'scenario' · 16:9 · 제품 약칭 · 공간) + `:start` → `conditions_route`,
  「장면별 이미지 모두 생성」 = `POST /v1/renders`(kind 'scene', 동시 1, 장면마다 한 번) → `GET /v1/renders/{id}` → 장면에 붙이고 `POST /v1/images/{id}/usages`.
  IMG4 결과는 `/scenario?image_version=&request=` → `POST /v1/image-returns` 로 해당 장면에 붙인다(SC4 진입 때 `images:sync` 로 충족된 요청도 붙임).

## 통합 세션 처리 — integration · 2026-10-07
- MI4 · VP4 「공간 시나리오」 진입이 비어 있던 것: 완료 — SC1(`pages/TypePage.tsx` + `seed.ts`)이 `?mi={analysis_id}`(`&personas=n`) · `?from=mi:` · `?from=vp:{vp_id}` 를 읽는다
  (웹이 게이트웨이로 `GET /api/mi/v1/analyses/{id}` · `…/result` 의 `user.personas` · `journey`, `GET /api/vp/v1/vps/{id}` 의 시트 `stakeholders` · `pillars` · `challenges` 를 읽음 — 서버 consumes 는 그대로).
  만들 때 원본의 `project_id` · 고객사를 잇고(`CreateScenario.customer_name` 추가 — 프로젝트 · Storyboard 고객이 없을 때만), 입력 줄 `[고객]` · `[인물] 역할 — 상황 · 원하는 것 · 불편한 점` · `[여정]` ·
  `[가치 · 역할] …` · `[과제]` · `[제품]` 과 등장인물(MI 페르소나)을 넣는다. 원문만 옮김(`[00]` 그대로). SC1 에 안내 한 줄(`sc1-seed`).
- SC2 입력 자동 저장이 첫 로드 직후 빈 값으로 덮어쓰던 것(디바운스 초기값 ''): 완료 — `pages/InputPage.tsx` 가 디바운스 값이 따라온 뒤에만 저장한다(Storyboard 공간 줄 · 위 재료가 잠깐 지워지던 것).
- SC5 → 제안서: 표준 · 퀵윈에 「solution」 섹션이 없으면 proposal 이 그 기능 기본 섹션으로 받고 응답 `section_key` 로 연다(SC5 웹이 응답으로 이동). 제안서를 지우면 사용 등록이 풀린다.
- `scenarios:from-birdseye` 가 프로젝트 · 고객을 조감도 handoff 에서 잇는다(안 주면).
- 참고: `make e2e-feature SERVICE=scenario` 의 `result.spec.ts:33` 은 mock 생성 속도(SC_PACE_S)가 0 이면(pm2 기본) 진행 화면을 못 보고 실패할 수 있다 — `SC_PACE_S=1.5 make dev-bg SERVICE=scenario` 로 돌리면 9개 모두 통과.
