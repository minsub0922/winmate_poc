# scenario 서비스 — 개발 세션 규칙

공간 시나리오 — 업종 템플릿 · 장면 작성 · 장면별 솔루션 · 장면 이미지 · 내보내기

- 포트: **5109** · 게이트웨이 경로: `/api/scenario/v1/...` · 파이썬 모듈: `winmate_scenario`
- 고칠 수 있는 경로(owns): `services/scenario/**`, `web/src/features/scenario/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`, `image`, `birdseye`, `storyboard`(새 흐름 허브 — `winmate_common.flow` 로만)
- 화면 수용 기준: `docs/scenarios/11-content-flow.md` §3 · §6(새 흐름) · `docs/scenarios/09-scenario.md`(이전 흐름) · 원본 보드: `docs/screens/` (INDEX.md)

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

**새 흐름(2026-10-08) · Storyboard 허브 연결 · 보드 webapp1 v58 SC0 · SC1 · SC2* · SC_Done · SC_DoneJson**
- 라우트: `/scenario` = SC0(셸 `ContentListScreen content="sc"`, 작성 중 초안은 `/v1/space-sets`) · `/scenario/new` = SC1(셸 `GateScreen`, `?sb=SB-NN&auto=1` 이면 바로 만듦 — DSS 완료 화면의 후속 작업) ·
  `/scenario/spaces/:id` = SC2(`FlowBar` = 실제 Storyboard) → 저장 → SC_Done(`FlowDoneView` · 전체 JSON · 「Storyboard로」). 코드 `web/src/features/scenario/spaces/`(FlowPages.tsx · SpacesPage.tsx).
- 이전 흐름 목록 · 새로 만들기는 `/scenario/legacy` · `legacy/new` · `legacy/new/template` · `legacy/new/birdseye`(lib.ts `route.*`). 다른 기능 · 서버 handoff 가 만드는 옛 주소는
  주소를 바꾸지 않고 이전 화면을 연다: `/scenario?image_version=`(IMG4) · `/scenario/new?sb=sb_…`(이전 Storyboard SB4) · `?from=` · `?mi=` · `?project=`(MI4 · VP4) · `new/template` · `new/birdseye`.
  `/scenario/:id/...` 는 그대로. `spaces/new` 는 `/scenario/new` 로 넘긴다(NewSpacesPage 는 지움).
- 만들기 `POST /v1/space-sets {sb_id}` → `get_flow` → `stages.dss` 의 공간 · 공간별 제품을 미리 채움(DSS 솔루션은 links 가 가리킨 공간에, 어디도 안 가리키면 고르기 목록에만).
  Storyboard 없음 404 `STORYBOARD_NOT_FOUND` · DSS 전 422 `PREREQUISITE_MISSING`. 문서에 `dss_ref`(공간 목록 머리 「공간 · DSS-01」 · `stages.sc.from`) · `dss_items`(SC2_Pick 묶음
  `DSS-01 · 제품` · `DSS-01 · 솔루션` · `카탈로그 · DSS에 없는 것`) · `customer`(AI 3안 익명화) · 요약본(AI 문맥). `spaces` 를 직접 주는 이전 본문도 그대로 된다.
- `:finish` → `ver`(저장 횟수) +1 → `push_stage(sb, "sc", ref=SC-NN, ver, res_id, title, value={from, spaces, rules, counts}, md, card)` → `{stage, summary_md, flow_sync}`.
  card = 공간 · 시나리오 · 시나리오 없는 공간 + 공간 3곳 묶음(`[확인 필요]` 시나리오는 「확인 필요」). 허브 편집 경로는 `/scenario/spaces/{id}`.
- 화면 보드와 다르게 한 것: 시나리오 지우기(목록 줄 오른쪽 아래) · 항목 빼기(입력칸 안 오른쪽)는 마우스 · 키보드가 머물 때만 보인다(쉴 때 보드와 같은 모습).
  직접 이름 지은 항목 이름은 라벨처럼 보이는 입력칸. AI 후보 근거는 안내 줄의 툴팁. 스텝바는 보드대로 SC1 · SC_Done 「공간별 시나리오」 · SC2 「공간 · 시나리오」.
- 시험: `tests/test_sc_flow.py` 3개(실제 storyboard 앱 — 404/422 · DSS 미리 채움 · 저장 → 허브 stages · cells.route · cards · contents · ver 2 · 분기) — pytest 62개.
  e2e `web/e2e/scenario/sc-flow.spec.ts` 2개(목록 → Gate → SC2 → 저장 → 완료 · 허브 확인 · 폭 196/236/662/908 · 본문 1180 · 높이 728 · auto · 옛 주소) ·
  `spaces.spec.ts` 는 Storyboard 없는 묶음(허브에 쓰지 않음). 캡처 `__screens__/SC0-new · SC0-list-new · SC1-new · SC2-new · SC2_AI-new · SC2_Pick-new · SC2_Empty-new · SC2_NoProduct-new · SC_Done-new · SC_DoneJson-new`.
- **DSS 다시 가져오기 · 초안 지우기 · 초안 이어 쓰기(2026-10-10 · 보드에 없음)**:
  - 묶음은 마지막으로 가져온 DSS 를 남긴다: `dss_ref` · `dss_ver` · `dss_spaces`(공간 이름) · `dss_items`(제품 · 솔루션과 놓인 공간). `GET /v1/space-sets/{id}` 는 이것과
    허브의 지금 stages.dss 를 견줘 `dss_changed{from, to, ref_changed, added, removed, changed, spaces_added, spaces_removed, added_names, removed_names}`(사람이 공간 제품을
    고친 것은 차이가 아님 · 없으면 null · DSS 로 만들지 않은 묶음은 늘 null). 다른 고침 응답(PUT 등)의 `dss_changed` 는 null(웹이 앞의 값을 잇는다).
  - `POST …/{id}:resync-dss`: DSS 에 새로 생긴 공간 → 공간 추가(`dss_status: added`), 있던 공간에 새로 놓인 제품 · 솔루션 → 공간 제품에 추가(added — 비교는 지난 DSS 기준이라
    사람이 일부러 뺀 DSS 제품은 DSS 가 그대로면 다시 넣지 않음), DSS 에서 빠진 (공간 · 제품) → 그 공간 시나리오 · 장면이 안 쓰면 빼고 쓰면 남겨 `dss_status: removed`(「DSS에서 빠짐」),
    시나리오는 지우지 않음, DSS 에서 빠진 공간은 시나리오도 제품도 없으면 빼고 아니면 removed. 지난 added 표시는 다음 다시 가져오기에서 지움. 저장한 묶음이면 status → draft.
    결과 `last_resync{from, to, added, removed, kept, spaces_added, spaces_removed, spaces_kept}`(항목은 「공간 · 제품」). `SSProduct` · `SSSpace` 에 `dss_status`(PUT 으로도 오간다).
  - `DELETE /v1/space-sets/{id}` 204 — 한 번도 저장하지 않은 것만(`ver` > 0 이면 저장 뒤 고쳐 draft 여도 409 `SAVED_CONTENT`), `unregister_item`.
    `POST /v1/space-sets {sb_id}`(Gate · spaces 없이)는 같은 Storyboard 의 DSS 로 시작한 저장 전 초안이 있으면 200 으로 그것(spaces 를 직접 주는 이전 시작은 이어 쓰지 않음). 코드 SC-NN 은 최댓값 + 1.
  - 화면: SC2 머리 아래 안내 줄(AiBar · 「Storyboard의 DSS가 바뀌었어요 · DSS-01 v1 → v2 · 제품 1 추가 · 1 빠짐 · 놓인 공간 1 바뀜 · 공간 1 추가」 · 「다시 가져오기」 —
    대기 중 자동 저장을 먼저 보내고 부른다). 줄(38 + 12)만큼 그리드만 줄고 칸 폭 196 · 236 · 662 · 본문 높이 728 그대로. 다시 가져오면 토스트 · 공간 줄 「새 공간」/「DSS에서 빠짐 · 시나리오 n」 ·
    공간 제품 칩 「새로」/「DSS에서 빠짐」(주황). SC0 저장 전 초안(ver 0) 줄은 `DraftRow.onDelete`.
  - 시험 pytest 64(+2: 다시 가져오기 합치기 · 시나리오 유지 · 새 공간 · 빈 공간 빼기 · ref 바뀜 / 지우기 · 이어 쓰기) · e2e `web/e2e/scenario/sc-resync.spec.ts` 1
    (캡처 `__screens__/SC2-resync-new.png` · `SC2-resynced-new.png`).

**새 흐름 · 공간 → 시나리오 → 장면 (2026-10-08 · `docs/scenarios/11-content-flow.md` §3 · 보드 webapp1 SC2*)**
- 백엔드 `spaceset.py` + `api_spaces.py` — `/v1/space-sets*`(DocStore `space_sets`, 코드 `SC-NN`). 스키마는 모두 `SS*` 접두.
  - 공간마다 제품 · 솔루션 1개 이상, 시나리오마다 공간 제품 중 1개 이상(어기면 `issues` · `:finish` 422 `SPACE_WITHOUT_PRODUCT` · `SCENARIO_WITHOUT_PRODUCT`).
  - `PUT`(expected_version 409)은 화면이 고친 그대로 저장. 후보 목록은 서버 기준이고 같은 id · cid 후보의 고친 내용만 받는다(수락 전 편집).
  - `spaces/{id}:suggest`: KB D1 사례 + `sc.space_candidates.v1` → 점선 3안 A/B/C. 모델이 없으면 사례 틀 + `[확인 필요]`(`mode=kb_only`). `candidates/{cid}:accept` · `DELETE`.
  - `:finish` → `stage`(= flow.json `stages.sc`) + `summary_md` + 허브 반영(위 절).
- 화면 `web/src/features/scenario/spaces/`(`/scenario/spaces/:id`). 자동 저장 600ms.
- 시험: `tests/test_space_sets.py` 4개 · e2e `web/e2e/scenario/spaces.spec.ts`. mock `mocks/ai-tools/sc.space_candidates.v1.json`.
- 이전 SC0~SC5 흐름은 그대로 둔다(제안서 handoff 가 아직 그것을 읽는다).

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
