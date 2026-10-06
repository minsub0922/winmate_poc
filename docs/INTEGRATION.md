# 통합(Integration) — 기능 사이 여정 · 넘김 규약

10개 기능(RQ · SB · MI · CA · VP · SP · IMG · BE · SC · PR)은 따로 만들어졌다. 이 문서는 **기능 사이를 잇는 규약**과 그것을 지키는 실제 스택 e2e(`web/e2e/integration/`)를 정리한다.
기능 안 수용 기준은 각 `docs/scenarios/*.md`, 서비스별 상태는 `services/<x>/AGENTS.md`, 요청 · 답은 `docs/requests/*.md`.

## 1. 돌리기

```bash
cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=integration WM_E2E_DEV=1 WM_E2E_PORT=5299 \
  npx playwright test e2e/integration --workers=1
```

- pm2 스택(게이트웨이 5000 · 10개 기능 + 워커 · `MODEL_MODE=mock`)을 그대로 쓴다. **`page.route` 흉내 없음.** Vite 개발 서버 5299.
- 약 4–6분(2026-10-07 이 머신 3.8분 — 재료 만들기 포함). 2 CPU 공유 머신이라 워커 1개, 파일 하나씩 돌려도 된다(`e2e/integration/02-proposal-journey.spec.ts`).
- 파일마다 `beforeAll` 이 API 로 재료를 만들고(제목에 꼬리표 `tag()`) `afterAll` 이 지울 수 있는 것을 지운다 — 정의서 · Storyboard 는 지우는 API 가 없어 남는다.
  기능 서비스가 게이트웨이에서 안 보이면 그 파일을 건너뛴다(`backendDown`). 각 파일은 `serial` — 앞 테스트가 실패하면 뒤는 건너뛴다.
- 도우미 `helpers.ts`: `seed*`(정의서 · Storyboard · MI · CA · VP · Spec · 이미지 · 조감도 · 시나리오를 API 로 끝까지), `until`(폴링), `clickIfShown`(뜰 수도 있는 확인),
  `cleanup`. 스크린숏 `web/e2e/integration/__screens__/`(J1 · J2 · J3).

### 1.1 전체 검증(통합 담당 · 2026-10-07 결과)

| 단계 | 명령 | 결과 |
|---|---|---|
| 계약 | `make contracts-check` | 17개 서비스 ✓ |
| 타입 | `cd web && node scripts/typecheck.mjs` | 오류 0 |
| 운영 빌드 | `cd web && npm run build` → 게이트웨이(5000)가 `web/dist` 서빙 | ✓ |
| 백엔드 | `uv run pytest libs/common services -q`(약 9분) | 974 통과 · 3 건너뜀(LibreOffice 필요) |
| 셸 e2e | `cd web && WM_E2E_SUITE=shell WM_E2E_DEV=1 WM_E2E_PORT=5197 npx playwright test e2e/shell --workers=1` | 138 통과(T-12 는 부하가 클 때 가끔 실패 → 다시 돌리면 통과) |
| 기능 e2e | `make e2e-feature SERVICE=<x>` | RQ 11 · SB 14 · MI 10 · CA 14 · VP 4 · SP 8 · IMG 20 · BE 6 · SC 9 · PR 25 |
| 통합 e2e | 위 1 | 25 |

- **진행 화면을 보는 e2e** 는 mock 이 너무 빨라 시연 속도를 줘야 한다: 이미지 `IMAGE_DEV_SHOT_DELAY_S=2.5`(run.spec.ts) · 시나리오 `SC_PACE_S=1.5`(SC4G).
  pm2 `restart --update-env` 는 셸에서 뺀 변수를 지우지 못한다 — 끝나면 `pm2 delete image-worker scenario-worker` 뒤
  `WINMATE_ONLY=image-worker,scenario-worker ops/node_modules/.bin/pm2 start ops/pm2/ecosystem.config.cjs` 로 다시 띄운다.
- 한 번에 모든 서비스 시험을 돌릴 때 시험 도우미 모듈 이름이 겹치면 안 된다(`conftest` · `scenario` 같은 이름 → `be_kit` · `ca_scenario` · `mi_scenario` 로 바꿈).

## 2. 여정 — 25개 모두 통과(2026-10-07)

| 파일 | 여정 |
|---|---|
| `01-rq-storyboard` (5) | RQ 파일(PPTX+TXT)로 채우기 → 바로 저장 v1 → RQ4 「Storyboard」 → SB1 정의서 골라짐 · SB 목차 저장 → RQ6 「쓰는 곳」 칩 · SB4 다음 카드 3 · SB4 「MI」 → MI1(정의서 · Storyboard 반입) · SB4 「공간 시나리오」 → SC 공간 · 고객 미리 채움 · **정의서 v2 저장 → SB 「v2가 새로 저장됐어요 · 저장 메모」 → 반영하기 → 링크 v2** |
| `02-proposal-journey` (11) | RQ6 「제안서」 → PR1(고객 · 프로젝트) → 표준 구성 · 각 기능의 「제안서로 보내기」: **MI4**(익명 확인) · **CA5**(Why Samsung CM · ST) · **VP4**(`?handoff=vho_` 띠 · CH · VP · EF) · **SP4**(`sho_` · in_sync) · **IMG4**(같은 프로젝트 제안서 기본 · 사용 이력) · **BE6**(BV · ZP + SM 은 공간별 제품) · **SC5**(표준 → 솔루션 섹션 SXS) · 사이드바 MI 끌어 놓기 → 추출 확인 → 반영 · 딸깍 → PR6 생성 → PR7 PPTX 받기 · 제안서 지우기 → 조감도 · 시나리오 · 이미지 · 정의서 · VP · Spec 표시 거둠 |
| `03-entries` (9) | RQ4 「MI」 → MI1 → 결과 → MI4 「새 제안서로 시작」 · CA1R `?input=requirements&rq=` → CA5 「새 제안서로 시작」 → 유형 고르면 why 섹션 · SB → VP `?sb=` → VP4 「새 제안서로」 · SP4 「새 제안서로 시작」 · BE6 「Spec 시작」 · IMG4 「새 제안서로 시작」 · 「조감도 참조로」 · BE6 「새 제안서로 시작」 · 「시나리오 시작」 → SC1B · SC4 「이미지 생성」 → IMG4 「공간 시나리오 장면으로」 → SC5 「새 제안서로 시작」 · SB4 「B2B 제안서」 → 섹션 「조감도 새로 만들기」 `?return_to=` · **MI4 · VP4 「공간 시나리오」 → SC 입력(페르소나 · 가치)** |

## 3. 기능 사이 규약(정리한 것)

### 3.1 id 접두사
- 작업: `rq_` 정의서 · `sb_` · `mi_` · `ca_` · `vp_` · `sp_` · `imw_`(이미지 작업) · `img_`(이미지) · `imv_`(이미지 버전) · `be_` · `sc_` · `pr_` · 반입 `imp_` · 잡 `job_` · 프로젝트 `prj_`.
- 넘김(handoff): `hof_` = **MI 와 CA 둘 다**, `vho_` = VP, `sho_` = Spec. `hof_` 만으로는 기능을 알 수 없으므로 **넘김에는 늘 작업 id 를 함께 보낸다**
  (`?handoff=hof_…&link=mi_…|ca_…`, 반입 `source.ref_id`). proposal 은 작업 id 접두사로 기능을 바로잡는다(`defs.feature_for_ref` · 웹 `lib/routes.handoffFeature`).
- 셸 끌기 참조: `ws:item:<id>`(사이드바 작업), 이미지 `img:image:<id>`, kb `kb:model:<code>`.

### 3.2 진입 주소(쿼리)
| 주소 | 쓰는 곳 |
|---|---|
| `/storyboard/new?rq=` · `/mi/new?rq=&sb=` | RQ4 · RQ6 · SB4 |
| `/competitor/new?input=requirements&rq=` | CA1R(정의서 미리 고름 — 최근 50개 밖이면 따로 읽어 맨 앞에) |
| `/vp/new?sb=` · `?mi=` · `?rq=` | SB4 · VP 시작 |
| `/spec/new?models=…&from={vp\|mi\|birdseye}:{id}` | VP4 · MI3V · BE6 → Spec origin |
| `/proposal/new?rq=` · `?sb=` · `?link={작업 id}[&feature=]` · `?handoff={hof_\|vho_\|sho_}&link={작업 id}[&feature=]` · `?image_version=imv_` | 각 기능 「새 제안서로 시작」 — PR1 이 연결 · 고객 · 프로젝트를 채운다 |
| `/proposal/{id}/sections/{key}?handoff=…&link=…` · `?oneclick=1` | 넘김 반입 띠 · 섹션에서 딸깍 |
| `/scenario/new?sb=` · `?mi={id}`(`&personas=n`) · `?from=vp:{id}` · `?project=` · `/scenario/new/birdseye?birdseye=` | SB4 · MI4 · VP4 · BE6 |
| `/scenario?image_version=imv_&request=irq_` | IMG4 「공간 시나리오 장면으로」 돌아오기 |
| `/birdseye/new?return_to=<제안서 섹션 경로>`(옛 `?return=`) · `?ref_version=imv_` | 제안서 「조감도 새로 만들기」 · IMG4 「조감도 참조로」 |
| `/image/new?request=irq_` | SC4 「이미지 생성」(IMG 요청) |

### 3.3 제안서로 보내기(넘김 → 반입)
1. 기능이 넘김을 만든다(`POST …/handoffs` — MI · CA · VP · Spec, 조감도 · 시나리오는 섹션 읽기만). 섹션 내용은 각 기능의 `GET …/proposal-handoff?type=&section=`(ProposalHandoff v1 — `items[{key, sheet_role, include_default, content}]`).
2. `POST /api/proposal/v1/proposals/{pr}/imports {section_key, via: 'handoff'|'drag_sidebar'|…, source: {feature, ref_id, version, handoff_id, title}, include_keys}`
   → 잡 `proposal.import_extract` → 넘김(via=handoff)은 바로 적용, 사이드바 끌기는 추출 확인 화면 → `:apply`.
3. 항목은 **역할로 섹션에 들어간다**(`ImportItem.section_key`): 조감도 수량표 SM → 「공간별 제품」, 시나리오 SXS → 「솔루션」 등. 그 유형에 없는 섹션으로 보내면 422 대신 기능 기본 섹션(`defs.WORK_TARGETS`)으로 — 웹은 **응답의 `section_key`** 로 연다.
4. include_keys(고른 시트 id)는 원본이 다시 짜도 **같은 id** 여야 한다(MI 시장 시트 MS ↔ MS+TR 고침). include_keys 가 없으면 `include_default`.
5. 넘김 확인(ack): VP `vho_:ack` → VP0 「연결된 제안서」, Spec `sho_:ack` → Spec 링크, MI · CA 는 웹이 `PATCH …/handoffs/{hof} {status:'delivered', target_id, target_title}`.

### 3.4 쓰는 곳 · 사용 표시
- 정의서 RQ6 「쓰는 곳」: 읽어 간 기능이 `PUT /api/requirements/v1/requirements/{rq}/links/{service}/{ref}`(internal), 지우면 `DELETE`. 제안서는 `rq_ref` 로 만들 때 등록, 지울 때 해제.
- 이미지 · 조감도 · 시나리오: `POST …/{id}/usages {service, ref, label, version}`(internal) → IMG 정보 「사용 이력」 · BE0 · SC0 「제안서에 사용 중」. 제안서는 반입 때 등록, 실행 취소 · **제안서 지우기** 때 `DELETE …/usages/proposal/{pr}`.
- VP · Spec: 넘김 ack 로 VP0 「연결된 제안서」 · Spec 연결(slk_)이 생기고, 제안서 지우기 · 그 원본의 마지막 반입 실행 취소 때 proposal 이
  `POST /api/vp/v1/vps/{vp}:release-proposal {proposal_id}` · `DELETE /api/spec/v1/links?proposal_id=[&sheet_id=]`(internal)로 거둔다.
- 프로젝트: 새 작업은 넘겨받은 작업의 `project_id` 를 잇는다(제안서 ← rq_ref · links · 이미지 작업의 workspace 항목, 시나리오 ← Storyboard · 조감도 · MI · VP). 같은 프로젝트 제안서가 「넣을 제안서」 기본값(IMG4 · BE6).

### 3.5 버전 전파
- Storyboard 는 20초마다 정의서 버전을 확인(`_RQ_CHECK_S`) → 목차 위 띠(「요구사항 정의서 v2가 새로 저장됐어요 · 변경 n건 · 저장 메모」) → 「반영하기」 → 링크 `rq_version` 갱신 · `up_to_date`.
- 제안서 섹션의 연결 자료 칩(`sources[].stale`) · 섹션 `needs_fill` 이 원본 변경을 알린다. Spec 링크는 `in_sync` · lifecycle 로 본다.

## 4. 고친 것(서비스별)
- **proposal**: 넘김 항목 역할 → 섹션 라우팅(`ImportItem.section_key` 추가) · 없는 섹션 대체(SC5 · BE6 → 표준 · 퀵윈) · 남의 역할을 옮긴 섹션 구성에 더하지 않음 · include_keys 없는 넘김의 `include_default`(VP EF 누락) ·
  `hof_` 기능 판별 · 프로젝트 · 고객 이어받기 · **제안서 지우기 · 반입 실행 취소 → 원본 쪽 표시 거두기**(조감도 · 시나리오 · 이미지 usages, 정의서 링크, VP 「연결된 제안서」, Spec 연결) ·
  VP 링크 제목 · ack `proposal_id` · `plan:confirm` 순서(요청) · 웹 `handoffFeature` · `return_to`.
- **mi**: 다시 짠 시장 시트 id 유지(MS ↔ MS+TR — MI4 → 제안서 MI 섹션 MS 가 늘 빠짐) · 설계 중 `GET …/design` 500 · MI3V → Spec `from=mi:`.
- **competitor**(웹): CA5 「새 제안서로 시작」 `TYPE_REQUIRED` → 넘김 + `/proposal/new?handoff=&link=&feature=competitor` · CA1R `?rq=` 가 최근 50개 밖 정의서면 따로 읽어 맨 앞에(엉뚱한 첫 정의서로 찾던 것).
- **vp**: internal `POST /v1/vps/{id}:release-proposal` · export 템플릿 확인 실패를 기억하지 않음.
- **spec**: internal `DELETE /v1/links?proposal_id=[&sheet_id=]`(연결 · 값 불일치 경고 · 보낼 제안서 거두기).
- **storyboard**: 정의서 새 버전 띠 한 줄(`rq_update.note` = 변경 수 · 저장 메모).
- **image**: mock 렌더 QC 「제품 수 다름」(요청) · 숨은 렌더 작업 색인 제외(+ 이미 올라간 36건 정리) · 「사용 이력」에 조감도 · 시나리오.
- **birdseye**(웹): BE6 기본 제안서 · 「열기」 섹션 · Spec `from=birdseye:` · BE1 `?return_to=`.
- **scenario**: SC1 `?mi=` · `?from=vp:` 재료(`seed.ts`, `CreateScenario.customer_name` 추가) · SC2 자동 저장이 미리 채운 입력을 ''로 덮던 것 · SC5 응답 섹션으로 이동 · `from-birdseye` 프로젝트 · 고객.
- 계약: proposal · scenario · spec · vp 추가만(깨지는 변경 없음, `make contracts-check` 통과). 서비스 테스트: proposal 28 · mi 120 · spec 56 · vp 30 · storyboard 42 · scenario 55 · image 74.
- 데이터 정리: 지운 제안서를 가리키던 정의서 링크 6건 · 조사용 제안서 · MI 작업.

## 5. 남은 틈(알려진 것)
- export 템플릿 상세 500 은 export 가 고쳤지만 pm2 의 export 재시작 전까지는 proposal 이 목록으로 대신 읽는다(동작 같음).
- kb · export 의 새 필드 안내(`docs/requests/{mi,competitor,birdseye,spec}.md` 의 「상태: 요청(kb → …)」 · spec XLSX 고객 양식 `base_file_id`)는 기능 몫 — 미반영(kb · export 재시작 필요).
- 정의서 → Spec 은 화면 진입 없이 프로젝트로만 잇는다(06-spec E1–E11 설계대로).
- 기능 e2e 참고: scenario `result.spec.ts:33` 은 `SC_PACE_S=1.5`(mock 생성 속도)가 필요, birdseye `inputs.spec.ts:41` 은 첫 실행에 가끔 느림(재실행 통과).
- 통합 e2e 는 정의서 · Storyboard 를 매번 새로 만든다(지우는 API 없음) — 개발 데이터가 쌓인다. 주인 없는 빈 제안서(제목 · 유형 없음) 몇 건은 출처를 몰라 남겨 두었다.

## 6. 통합 담당 할 일
- pm2 재시작: `kb`(새 필드) · `export`(템플릿 상세 · XLSX 양식) — 그 뒤 기능 세션이 새 필드를 쓰게.
- requirements · storyboard 에 지우기(또는 보관) API 가 생기면 `helpers.cleanup` 에 더한다.
- 새 기능 간 진입을 만들면 3.2 표와 `03-entries` 에, 새 「보내기」는 `02-proposal-journey` 에 한 줄씩 더한다.
