# mi 서비스 — 개발 세션 규칙

Market Intelligence — 업종 판별 · 4개 분석 영역 · 출처 검증 · 부분 재분석 · 보고서

- 포트: **5103** · 게이트웨이 경로: `/api/mi/v1/...` · 파이썬 모듈: `winmate_mi`
- 고칠 수 있는 경로(owns): `services/mi/**`, `web/src/features/mi/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`, `requirements`
- 화면 수용 기준: `docs/scenarios/03-mi.md` · 원본 보드: `docs/screens/` (INDEX.md)

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=mi          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=mi         # 이 서비스 테스트
make contracts SERVICE=mi    # contracts/mi.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("mi", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("mi")`(data/mi/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=mi` 를 돌리고 `contracts/mi.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태 (2026-10-06)
03-mi 의 보드 18장(UC_MI 유스케이스 맵 · MIC 시나리오 픽스처는 라우트 없음 → 화면 16 + 공유 보기) · 수용 기준 AC-MI-01~94 를 구현했다.
pytest 118 · e2e 10(실제 스택 5 + API 흉내 5) 통과(MODEL_MODE=mock).

### 코드 지도 (`src/winmate_mi/`)
| 파일 | 하는 일 |
|---|---|
| `api.py` | 정보 · 라우팅 규칙(MIR) · capabilities · 업종(목록 · 인사이트 · 판별) · 작업 CRUD · 복제 · 반입(storyboard · requirements) · 버전/복원 · 셸 추가(additions) · 설계(+메모) · 경쟁사 · 기준 · 실행 · 진행 |
| `api_results.py` | 결과(MI3) · 주장/출처(MI3S) · 출처 추가/빼기 · 질문 · 후속 질문 · 한 장 요약 · 확정 필요 항목(MI3V: 입력 · 되돌리기 · 스캔 · 말로 알려주기 · 고객 질문 · 적용) |
| `api_more.py` | 부분 재분석(MI3R) · 시트 구성/후보/레이아웃(MI3P · MI3L) · 구성 요청 · 넘김(handoffs) · 묶음(bundle) · 근거 스냅숏(evidence) · ProposalHandoff · facts:lookup · 내보내기 · 공유 · export-view · shared-view · table-text · 재확인 · 경쟁사 분석 반입 |
| `models.py` | 모든 요청/응답 모델(= `contracts/mi.json`, 64 경로) |
| `service.py` · `views.py` · `deps.py` · `store.py` · `versions.py` | 작업 문서 · 화면 모양(목록 행 · 메뉴 · 설계 결정 · 결과 뷰) · 잡 넣기 · DocStore(`mi`) · 결과 버전(kind full/auto/revision/fix/layout/restore) |
| `rules.py` · `config.py` · `config/*.yaml` | 결정 규칙(라우팅 임계 · 시간/ETA 문구 · 조사 josa) · 16업종(`segments.yaml`) · 라우팅(`routing.yaml`) · 시트 템플릿(`templates.yaml`) |
| `claims.py` · `verify.py` · `fixes.py` | 주장 · 인용 대조(summary_only: 요약문에 없는 인용은 버림 · 숫자 `[00]`) · 충돌 · 확정 필요 항목 |
| `layout.py` · `bundle.py` · `anonymize.py` | 시트 고르기(업종 레이아웃 · CP 적합도) · 넘김 묶음/ProposalHandoff/내보내기 원본/근거 스냅숏(같은 익명 · 대외비 규칙) · 경쟁사 표기 |
| `aix.py` · `prompts.py` · `kbx.py` · `rqx.py` | `ai()` 호출(task `mi.*`, 고객 자료면 `confidential=True`) · 프롬프트/스키마 · kb · requirements 어댑터 |
| `graphs/` · `worker.py` | LangGraph — design(interrupt 로 업종 묻기) · analyze(계획 → 영역별 수집 → 주장 → 비교표 · 강점 → 시트) · revise · misc · competitors |

### 잡 · 모델 호출
- 잡 kind 12: `mi.design` · `mi.analyze` · `mi.revise` · `mi.fixscan` · `mi.layout` · `mi.source_add` · `mi.competitor_add` · `mi.onepager` · `mi.export` · `mi.recheck` · `mi.import_ca` · `mi.facts_research`.
- 진행: `step` 이벤트에 `stage` 스냅숏(`stages` · `areas` · `sources` · `recent_sources` · `previewable`), `progress` 에 `progress` · `eta_s`. 메모 반영은 log `메모를 반영했어요 · …`.
- 목 픽스처 `mocks/ai-tools/mi.*.json` 42개(요약형 웹 검색 · A 커피 FB 시나리오). 실제 데모: 설계 ~3초 · 분석 ~10초.

### 웹 (`web/src/features/mi/`)
| 라우트 | 보드 |
|---|---|
| `/mi` | MI0 목록(머리 집계 · 상태 탭 · 업데이트 배너 · 행 동작/메뉴 · 업종 칩) |
| `/mi/rules` · 시트 | MIR 라우팅 규칙(MI2A · MI1Q 의 `판단 규칙` · `언제 묻는지 보기` 는 시트로) |
| `/mi/new` · `/mi/:id/input` | MI1(800ms 뒤 draft · Storyboard 가져오기 · 파일) |
| `/mi/new/industry` · `/mi/:id/industry` | MI1I 업종 인사이트 프리셋 |
| `/mi/:id/design` · `/design/industry` | MI2A 분석 설계 · MI1Q 업종 묻기(바꾸기 모드 포함) |
| `/mi/:id/scope` · `/competitors` | MI2 범위 · MI2C 경쟁사 · 기준 · 가중치 |
| `/mi/:id/run` | MI3G 진행(`?then=slides` 는 MI3L 데이터 보강 잡) |
| `/mi/:id/result` (`?tab=&version=&preview=1&panel=sources&claim=`) | MI3 결과 · MI3S 출처 패널 |
| `/mi/:id/verify` · `/revise` · `/slides` · `/slides/:sheet` · `/export` · `/shared` | MI3V · MI3R · MI3P · MI3L · MI4 · 공유 보기 |
- 공용: `api.ts`(경로는 여기만) · `hooks.ts` · `lib.ts`(ETA · 가중치 % · 조사 · 복사) · `parts.tsx` · `blocks.tsx` · `mi.css`(토큰만).
- 다른 기능은 웹이 잇는다: 제안서 가져오기 `POST /api/proposal/v1/proposals/{id}/imports`(계약 없음 — e2e 흉내), Storyboard 읽기 · Key Message 근거 쓰기.

### 결정 · 문서와 다른 점
- 실행 `mode`: `full` · `auto`(바뀐/실패 영역만) · `changed_only`(영역 없으면 `upd_changes` 의 영향 영역) · `resume`.
- 설계는 업종을 묻기 전에 나머지 결정을 먼저 만든다(MI1Q 아래 `자동으로 정한 것`). MIX 표준 섹션은 사용자 시트를 쓴다.
- 문서에 없던 화면용 API: `progress` · `export-view` · `shared-view` · `table-text` · `evidence`(Key Message 근거 스냅숏) · `SlidePlan.status/status_label`(MI4 매핑 상태).
- `mi.url_candidates` · `mi.summary_extract` task 는 따로 두지 않았다(수집 노드에 합침). 셸 추가는 이름으로 kb 참조를 푼다. 강점 LLM 실패 시 규칙 기반 강점.
- MI3 업종 칩 → 업종 시트(모달)에서 고정 후 `auto` 재실행(MI3R 아님). MI2A `쓰임` · `사내 자료` 바꾸기는 모달(Q10). MI1Q 바꾸기 모드 큰 버튼 `{업종}로 바꾸기`.
- MI2C 익명 꺼짐이면 에이전트 말 `내부용이라 경쟁사 실명을 그대로 써요.` MI2 는 설계가 범위를 정하기 전엔 4영역을 기본으로 보인다.
- 화면마다 `last_screen` 을 PATCH 해 `/mi/:id` 가 마지막 화면으로 연다. 제안서 이동 `/proposal/{id}/sections/mi|bigMi` · `/proposal/new?link=mi_…`(셸 키 기준).
- MI4 `Storyboard · Key Message에 근거로 붙이기` 는 시트에서 Key Message 를 골라 근거마다 storyboard evidence API 를 부른다(02-storyboard §8.3).
- 제목 기본값 `{고객사} {주제} 분석`, 고객사가 없으면(MI1I 프리셋) `{업종} {주제} 분석` — 목록 · 사이드바가 `새 분석` 으로 채워지지 않게. 조사는 `rules.josa`(`AS는` · `v3으로`).

### 요청한 것(docs/requests)
- kb: R01~R24 이름표 · 6업종(SV · TP · VN · AD · ID · OE) 대응. workspace: ModeChip · SourceCard · EvidencePanel 키트 부품.
- proposal: imports(`source.handoff_id`) · 섹션 경로 · PR 항목 `meta.proposal_type`. platform: storyboard 간선(선택) · consumes 확인.

### 테스트
- `make test SERVICE=mi`: pytest 118(`tests/scenario.py` 공용 시나리오 = MIC 1번 · 플랫폼 앱 in-process · kb 실데이터 · requirements 통합 1 · `test_mock_demo` 는 실제 목 픽스처로 한 바퀴 ·
  `test_rules.py` 의 MIC 12케이스 업종 판별 표).
- `make e2e-feature SERVICE=mi`(약 1분): `web/e2e/mi/` flow(실제 스택 2 — MI3S~MI4 · Key Message 근거 시트 포함) · more(실제 스택 3: 프리셋 · 가중치 · 재분석 → 제안서) ·
  screens(API 흉내 5: MI1Q · MI3G 미리 보기 · MI3S 배지 · MI0 보드 · MI1 draft). 제안서 imports · storyboard 는 `page.route` 흉내.
  스크린숏 `web/e2e/mi/__screens__/`. 공유 개발 데이터라 테스트가 자기 작업을 만든다(`helpers.ts` seedDesigned · seedDone).

### 통합(integration · 2026-10-07)
- 시트 다시 짜기(`layout.sheet_plan`)가 시장 시트를 MS ↔ MS+TR 로 불러도 같은 id 를 잇는다 — 리포트로 분석하고 표준 제안서로 넘기면 MS 가 고른 id 와 안 맞아 빠지던 것(제안서 MI 섹션 MS 가 늘 비어 있음). 테스트 2개 추가(pytest 120).
- 설계 잡 중간 `GET …/design` 500(덜 만든 결정 줄) → 다 만든 줄만 보인다. MI3V → Spec `from=mi:{id}`. MI4 「공간 시나리오」 링크는 scenario SC1 이 페르소나를 등장인물로 받는다.
