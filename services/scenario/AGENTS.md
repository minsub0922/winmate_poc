# scenario 서비스 — 개발 세션 규칙

공간 시나리오 — 업종 템플릿 · 장면 작성 · 장면별 솔루션 · 장면 이미지 · 내보내기

- 포트: **5109** · 게이트웨이 경로: `/api/scenario/v1/...` · 파이썬 모듈: `winmate_scenario`
- 고칠 수 있는 경로(owns): `services/scenario/**`, `web/src/features/scenario/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`, `image`, `birdseye`
- 화면 수용 기준: `docs/scenarios/09-scenario.md` · 원본 보드: `docs/screens/` (INDEX.md)

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=scenario          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=scenario         # 이 서비스 테스트
make contracts SERVICE=scenario    # contracts/scenario.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("scenario", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("scenario")`(data/scenario/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=scenario` 를 돌리고 `contracts/scenario.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태
- 화면 12개 + UC_SC(개발용) 구현(`web/src/features/scenario/`): SC0 목록 · SC1 유형(+조감도 추가) · SC1T 업종 템플릿 · SC1B 조감도에서 이어 만들기(+변경 반영 모드) ·
  SC2 입력(+텍스트 보기) · SC2E 타임라인 · SC3 솔루션 · 제품 · SC3R 추천 · SC4G 생성 중 · SC4 결과 · SC4E 장면 편집 · SC5 보내기. 라우트는 `index.tsx`.
- API 65개(경로 59, `contracts/scenario.json`). 다른 서비스용(internal): `GET …/handoff`(§8) · `GET …/proposal-handoff`(ProposalHandoff v1, section=spaceScenario|solution) ·
  `POST/DELETE …/usages`(제안서 사용 등록 → SC0 「제안서에 사용 중」).
- 워커 잡(LangGraph, thread=job_id): sc.parse_input · sc.skeleton · sc.timeline_edit · sc.lane_rewrite · sc.recommend · sc.generate(장면 나누기 → 장면별 쓰기(스트리밍) →
  솔루션 · 제품 연결 → [00] 표시, 메모 · 취소 · 같은 thread 재개) · sc.rewrite_scene · sc.edit · sc.shorten · sc.images_batch(image 렌더 동시 1) · sc.export.
- 모델: `ai()` task `sc.*`(mock 응답 `mocks/ai-tools/sc.*.json`). 고객명 들어간 호출은 confidential → 403 POLICY_CONFIDENTIAL 이면 익명화 → confidential:false 재시도 →
  이름 복원 · `anonymized=true`. 경쟁사 사전(`config/content_policy.yaml`, 「경쟁사 …」 일반 패턴 포함)은 결과에서 「기존 시스템」으로 치환. 근거 없는 수치는 `[00]`.
- 시험: pytest 55개(`make test SERVICE=scenario`) — AC1–54 백엔드 쪽 + 실제 image · birdseye 앱 in-process 통합, Storyboard 계약 모양 가짜.
  e2e 9개(`web/e2e/scenario/`, 캡처 `__screens__/` 15장, 1 worker · 파일마다 retries 1 — 공유 PC 메모리 부족으로 탭이 죽는 일 대비).
  SC1B e2e 는 테스트 세계에서 뽑은 응답(`fixtures/birdseye.json`)을 네트워크에서 바꿔 끼운다. SC4G e2e 는 `SC_PACE_S=1.5 make dev-bg SERVICE=scenario` 로 띄워야 진행 중 화면이 잡힌다.
- 정해 둔 것:
  - workspace 색인 `feature` 는 계약 enum 코드 `"SC"`(문서의 'scenario' 대신). route 는 상태별(`/type` · `/input` · `/timeline` · `/solutions` · `/generate/{job}` · `/result`).
  - 제안서 넣기는 제안서 계약 모양: `POST /api/proposal/v1/proposals/{id}/imports {section_key:'spaceScenario', via:'handoff', source:{feature:'scenario', ref_id, version, title},
    include_keys:['VM-A:1', …]}`(문서의 `{source:{service,id}, section:'space_scenario', sheet_plan}` 대신). 제안서가 proposal-handoff 를 읽고 usages 를 등록한다.
  - 저장 버전은 DocStore 버전과 따로 `saved_version`(응답 `version`), DocStore 버전은 `rev`. 생성 완료 · 「저장」 때 오른다.
  - 장면 이미지 「사내 자산 · 내 이미지에서 고르기」는 셸 이미지 팝오버(`useOpenPopover('image')` + onAdd) → `image:attach {image_ref: img:image:… | kb:image:…}`.
    image 흐름(IMG4) 결과는 `/scenario?image_version=&request=` → `POST /v1/image-returns` 로 장면을 찾아 붙인다. SC4 진입 때 `images:sync`.
  - SC4 「조감도 추가」: 연결이 있으면 BE5Z(`/birdseye/{id}/zones?scenario=`), 없으면 팝오버(새로 만들기 · 기존 연결).
  - 조감도 변경 반영(resync)은 연결 때 남긴 존 스냅숏(`birdseye_link.zones`)과 지금 handoff 를 제품 서명으로 비교 — 바뀐 존의 장면만 장소 · 제품 갱신(사용자가 더한 제품은 남김),
    `story_check` · 이미지 stale.
  - 수정 요청 · 다시 쓰기의 「새로」 · 「바뀐 곳」 기준은 직전 확정 버전. 「바뀐 곳 {k}」는 장면 하나 GET(SC4E)에서만 계산한다.
  - VM-D 열은 장면이 있는 시간대만. 시트 구성 공간 정규화(sc.space_keys)는 한 번 저장해 다시 쓴다.
  - mock 시연 속도 `SC_PACE_S`(장면마다 쉬는 초, 기본 0) · LLM 재시도 간격 `SC_LLM_RETRY_DELAYS`(기본 1,3) — `.env.example` 등록은 platform 요청.
- UC_SC 유스케이스 맵은 개발용 `/scenario/uc`(레인 5 · 카드 17).
- 남은 것 · 확인 필요: 제안서가 반입 뒤 usages 를 등록하지 않음(요청 `docs/requests/proposal.md` — 등록되면 SC0 「제안서에 사용 중」, e2e 가 자동 확인),
  birdseye 실데이터(존 있는 조감도)로 SC1B 전체 확인.

**통합(integration · 2026-10-07)**
- SC1 `?mi=` · `?from=mi:` · `?from=vp:` → `seed.ts`(MI 페르소나 · 여정 / VP 가치 · 과제 · 제품을 입력 줄 · 등장인물로, 프로젝트 · 고객 이어받기 — `CreateScenario.customer_name` 추가).
- SC2 자동 저장이 첫 로드 직후 미리 채운 입력을 ''로 덮던 것 고침. `scenarios:from-birdseye` 는 조감도의 프로젝트 · 고객을 잇는다. SC5 는 응답 `section_key` 로 제안서 섹션을 연다.
- 위 「남은 것」의 제안서 usages 등록은 proposal 에서 완료(반입 시 등록, 실행 취소 · 제안서 지우기 시 해제).
