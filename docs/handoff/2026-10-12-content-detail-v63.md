# 웹앱 ① v63 — 콘텐츠 상세를 「최종본에서 바로 고치기」로 (서비스 세션 공통 지침 · 2026-10-12)

사용자 결정(2026-10-12):
- 각 콘텐츠 상세에서 **팝업 단계 안에 최종본이 있으면 팝업으로 띄우지 않고 최종본 상태에서 바로 수정**한다.
  예: 고객 요구사항은 팝업이 필요 없다 — **최종 형태에 입력 · 수정 · 저장**한다.
- **사전으로 Storyboard 를 고르는 콘텐츠는 목록에서 누르면 바로 Storyboard 고르기 팝업 → 고르면 그 콘텐츠 페이지로 넘어간다.** 그 다음 팝업은 필요한 것만.

정리한 규칙(보드 FlowRule 7): 상세는 최종본 한 장 · 그 자리에서 입력 · 수정 · 저장. 팝업은 따로 하는 일(Storyboard · 제품 · 솔루션 고르기, MI 검색)에만.
새로 만들던 것은 작성 중으로 남고(자동 저장), 저장된 것을 고치다 나가면 저장할지 묻는다.
v60(완료 화면 대신 콘텐츠 보기) · v62(단계 팝업)를 코드에 옮긴 적이 없으므로, **이번에 v63 하나로 바로 간다**: 완료 화면(FlowDoneView) · 단계 페이지(`?step=` 등) 모두 없앤다.

## 먼저 읽을 것
1. 루트 `AGENTS.md`, 맡은 `services/<x>/AGENTS.md`, `docs/scenarios/11-content-flow.md` §1 · §5 · §6(허브 · stage 계약은 그대로)
2. 보드(원본 · 그린 결과): `docs/screens/webapp1/<보드>.dc.html` · `docs/screens/_rendered/webapp1/<보드>.jpg`(Read 로 본다) · `.txt`
   - 공통: `View`(머리 · 저장 · 본문 자리 · 후속 · 팝업) · `Gate`(목록 위 팝업) · `List` · `SBBar` · `JsonPopup` · `ProdPicker` · `FlowRule`
   - **콘텐츠 본문 보드가 정본**: `RQBody` · `DSBody` · `MIBody` · `CABody` · `VPBody` · `SPBody` · `SCBody`(+ 팝업 `SolPicker` · `MISearch`)
     — 각 본문 보드는 `mode` 4가지(saved · editing · new · draft)와 AI(점선) 상태를 한 파일에 그린다. 래퍼 보드(아래 표)는 그 상태를 고른 화면.
3. 이전 구현(지금 코드): `web/src/features/<x>/…` 의 새 흐름 페이지(v58 — Gate 페이지 · 단계 페이지 · FlowDoneView). API · 훅 · 행동(actions)은 대부분 그대로 쓴다.

## 공용 부품(이미 있음 — 고치지 말고 쓴다. 부족하면 보고서에 적는다)
웹 `@/shell`:
- `ContentDetail` — 보드 View 그대로의 틀: SBBar(FlowBar) · 머리(아이콘 44 · 제목 22 · 참조 알약 · 한 줄 · 「눌러서 바로 고쳐요」/ 「고친 곳 n · 되돌리기」 · flow.json · 저장) · 본문 · 후속 작업 · flow.json 팝업 · **고치다 나가면 묻기(useBlocker)**.
  ```tsx
  <ContentDetail content="dss" saved={doc.ver != null} changes={doc.changes} empty={…새로 만들기인가}
    title={doc.title} refCode={doc.code} ver={doc.ver} savedAt={doc.saved_at} updatedAt={doc.updated_at}
    facts={['공간 7', '제품 12', '솔루션 3']}          // 보드 View 머리 한 줄(저장됨) · 작성 중 줄에도 쓰인다
    sbIds={doc.sb_ids ?? [doc.sb_id]} onSave={finish} onRevert={revert}
    savedToast={(out) => `DSS-01 v2 저장 · …`} actions={<XLSX 버튼/>} canSave={true | '이유'}
    nexts={[{ key: 'sc', title: '공간 시나리오 생성', desc: '…', ref: 'SC-01 v1' | null, to: '…' }]}>
    {본문 — cd-body 안을 채운다: 최상위 요소는 flex: 1 1 0; min-height: 0 로 높이를 채우고 패널 안에서만 스크롤}
  </ContentDetail>
  ```
  상태는 `detailMode({saved, changes, empty})`: saved(고친 곳 0) · editing(고친 곳 n) · new · draft. useShellPage 는 ContentDetail 이 부른다(스텝바 없음 — 보드에 없다).
- `GateScreen({content, onStart, initialSb, autoStart, drafts})` — **이제 목록 위 팝업**(보드 Gate 880×780). `/<base>/new` 라우트에 그대로 두면 된다
  (목록 「새 ○○ 만들기」 링크가 이 주소라 누르는 즉시 팝업). 닫으면 `/<base>`. `?sb=&auto=1` 은 그대로 자동 시작.
- 인라인 편집 조각: `InlineInput({value, onCommit, label, changed, multiline, placeholder, className})`(칸을 떠날 때 · Enter 에 한 번 저장) ·
  `AiButton({children, onClick, busy, size: 28|32|36})`(✦ 파란 테두리) · `PendingBar({count, text?, onAcceptAll, onClearAll})`(점선 일괄 줄).
- 공용 클래스(`web/src/shell/flow/detail.css`): `cd-in`(칸) · `cd-in--soft` · `cd-in--bare` · `cd-in--warn`([확인 필요] 노란 칸) · `cd-in--chg`(이번에 고친 칸) · `cd-chgrow`(고친 줄) ·
  `cd-pend`(AI 점선) · `cd-aib` · `cd-ok`(수락) · `cd-x`(×) · `cd-add`(점선 더하기) · `cd-link` · `cd-tag cd-tag--man|manline|ai|pend|warn|chg|pill` · `cd-strip`(흰 띠 48) · `cd-panel` · `cd-sr`.
  기능 CSS 는 기능 폴더의 접두어 클래스로(보드 px 그대로). 색은 `var(--wm-*)`.
- 그대로: `ContentListScreen` · `FlowBar` · `SBPopup` · `ContentPopup` · `useFlow` · `CONTENT` · `whenText`, `@/ui` 의 `Modal` · `ProductPickerDialog`(보드 ProdPicker) · `JsonPopup` · `toast` · `Skeleton` · `ErrorState`.

백엔드 `winmate_common.edits`(새로 — `libs/common/src/winmate_common/edits.py` 머리 주석): `SNAPSHOT` · `take_snapshot` · `ensure_snapshot` · `snapshot_view` · `restore_snapshot` · `changes_of`.

## 하는 일(서비스마다)
### 1. 백엔드 — 「고친 곳 n · 되돌리기」
문서는 칸을 고칠 때마다 바로 저장(지금처럼). 저장(`:finish`)이 Storyboard 에 반영하는 판을 만든다. 저장 뒤 다시 고치면 차이를 센다.
- `EDIT_KEYS`(사람이 고치는 문서 키 — 메타 · 판 번호 · AI 후보 목록은 빼도 된다)를 정한다.
- `:finish` 의 갱신 함수 안에서 `doc[SNAPSHOT] = take_snapshot(doc, EDIT_KEYS)`. 허브에서 가져와 만든 저장 문서(있으면)에도.
- 문서 응답 모델에 `changes: int = 0`(저장한 적 없으면 0). 계산: `changes_of(stage(doc), stage(snapshot_view(doc, EDIT_KEYS)))` — `stage(…)` 는 그 서비스의 flow.json 값 함수.
  예전에 저장해 판이 없는 문서는 읽을 때 `ensure_snapshot(doc, EDIT_KEYS, saved=…)` 로 지금 값을 판으로 남긴다(한 번 다시 쓴다).
- `POST /v1/<자원>/{id}:revert` → 저장한 판으로 되돌린 문서(changes 0). 저장한 적 없으면 409 `NOT_SAVED`(「아직 저장하지 않아 되돌릴 판이 없어요」). 응답 모델은 문서 모델 그대로.
- 테스트: 저장 → 고치기 → `changes` > 0(목록 앞에 하나 끼워도 1) → `:revert` → 값 · changes 0 → 다시 저장 v2. 기존 테스트는 모두 통과.
- `make test SERVICE=x` · `make contracts SERVICE=x`(웹 API 타입도 생긴다) · `make contracts-check`. 고친 백엔드는 `ops/node_modules/.bin/pm2 restart <x>`(워커가 있으면 `<x>-worker` 도).

### 2. 웹 — 상세 한 장
- 라우트: 목록 `/<base>`(ContentListScreen · 그대로) · 새로 `/<base>/new` = `GateScreen`(이제 목록 위 팝업) · **상세 = 허브 `cells[].route` 경로 하나**(§6: rq `/requirements/flow/:id` · dss `/dss/:id` ·
  mi `/mi/flow/:id` · ca `/competitor/flow/:id` · vp `/vp/values/:id` · sp `/spec/flow/:id` · sc `/scenario/spaces/:id`). 단계 쿼리(`?step=` 등)와 완료 화면은 없앤다(예전 주소로 와도 상세가 뜨면 된다).
- 상세 = `ContentDetail` + 본문 보드(<X>Body) 그대로. 저장 전(new · draft) · 저장됨(saved) · 고치는 중(editing) 모두 **같은 화면**이다. 저장하면 그 자리에서 saved 로 바뀐다(문서 다시 읽기).
- 칸은 바로 고친다: 글은 `InlineInput`(떠날 때 저장) · 고르기 · 토글은 누르는 즉시. 고친 결과는 서버 `changes` 로 머리에 뜬다.
  **이 화면에서 고친 칸은 `cd-in--chg`(줄은 `cd-chgrow`)로 표시**한다(화면 상태로 기억 — 저장 · 되돌리기 하면 지운다).
- AI 추가기능은 버튼으로만, 결과는 점선(`cd-pend`) · 수락(`cd-ok`) · ×. 여러 개면 `PendingBar`.
- 팝업은 보드에 [팝업]으로 적힌 것만(아래 표). 단계 팝업 · 「다음 단계」 버튼 · 스텝바는 없다.
- 후속 작업(`nexts`): 그 Storyboard 에 이미 있으면 「참조 vN · 열기」(허브 cell route), 없으면 `/<base>/new?sb=<id>&auto=1`(사전 작업 고르기를 건너뜀).
- 목록 카드의 초안 단계(`DraftRow.step`)는 지금처럼 계산해도 된다.
- **보드를 철저히 따른다**(px · 문구 · 줄 순서 · 버튼 위치). 보드와 다르게 한 곳은 보고서에 「보드와 다름: 무엇 · 왜」.

### 3. e2e
`web/e2e/<x>/` 의 흐름 · 초안 스펙을 새 화면으로 고친다: 목록 → 「새 ○○ 만들기」→ 팝업에서 Storyboard 고르기 → 상세(새로 만들기) → 바로 입력 → 저장 → 저장됨
→ 한 칸 고치기 → 「고친 곳 1」→ 되돌리기 / 저장 · v2. 보드 고정 칸 폭을 숫자로 재고 `__screens__/<보드>.png` 를 남겨 `_rendered` 와 나란히 본다.
초안 지우기 · DSS 다시 가져오기 등 기존 기능 e2e 는 셀렉터만 바꿔 유지한다. 실행: `make e2e-feature SERVICE=<x>`.

## 콘텐츠별 보드 · 팝업
| 콘텐츠 | 래퍼 보드(상태) | 본문 보드 | 팝업으로 남는 것 |
|---|---|---|---|
| 고객 요구사항 | RQ0(목록) · RQ1(새로 · 빈 최종본) · RQ_Draft · RQ1_Edit(고치는 중) · RQ_View(저장됨 · 후속 DSS) | RQBody | 없음(목록 「새 요구사항 만들기」→ 바로 빈 최종본) |
| DSS | DS0 · DS1(목록 위 Gate) · DS2(새로) · DS2_AI · DS_Draft · DS2_Edit · DS_View(후속 시나리오 · Spec) · DS_ViewJson | DSBody | 솔루션 고르기 DS4 · DS4_AI(SolPicker 820×700) · 제품 탐색 고르기(ProdPicker) |
| MI | MI0 · MI1 · MI1_Branch · MI2_Loading · MI2 · MI2_Run(검색 중) · MI3(찾은 정보 그 자리에서 담기 · 문장 고치기) · MI3_Edit · MI_View · MI_Search · MI_Draft | MIBody | 검색 MISearch(1040×740) — 새로 만들면 들어오자마자 열림(AI 분석 → 검색어 · 조건 → 웹 검색) · 저장된 것은 「검색어 · 조건 고치고 다시 검색」 |
| 경쟁사 분석 | CA0 · CA1 · CA2(새로 · 경쟁사 없음) · CA_Draft(제안 기준 비교) · CA2_Info · CA2_Pc · CA2_AI · CA2_Edit · CA_View(경쟁사별) · CA_Table(비교표) | CABody | 없음(보기 전환 「경쟁사별 · 비교표」) |
| VP | VP0 · VP1 · VP2(새로 · DSS 제품 · 솔루션 가져옴) · VP_Draft · VP2_AI · VP2_Edit · VP_View | VPBody | 제품 · 솔루션 고르기 VP2_Pick(ProdPicker) · 연결된 가치 전체 VP2_Detail(VpDetail 900×720) |
| Spec 시트 | SP0 · SP1 · SP2(새로 · DSS 제품으로 표) · SP_Draft · SP2_Edit · SP_View(XLSX) | SPBody | 제품 고르기 SP2_Pick(ProdPicker) |
| 공간 시나리오 | SC0 · SC1 · SC2(새로 · DSS 공간 · 제품) · SC_Draft · SC2_AI · SC2_Empty · SC2_Edit · SC_View | SCBody | 공간 제품 · 솔루션 고르기 SC2_Pick(ProdPicker) |

## 같이 일하는 법(중요)
- 여러 세션이 **같은 작업 트리 · 같은 pm2 스택**을 동시에 쓴다. 이 머신은 CPU 2개 · 메모리 7GB 다. 무거운 명령은 반드시 잠금으로 줄을 세운다:
  `flock /tmp/wm-heavy.lock make typecheck SERVICE=x` · `flock /tmp/wm-heavy.lock make e2e-feature SERVICE=x` · `flock /tmp/wm-heavy.lock make test SERVICE=x`.
- 고칠 수 있는 곳: `services/<x>/**` · `web/src/features/<기능>/**` · `web/e2e/<기능>/**` · `contracts/<x>.json` · `web/src/api/gen/<x>.ts`(make contracts 가 씀) · `mocks/ai-tools/<자기 task>*`.
  `web/src/shell` · `web/src/ui` · `libs/common` · `config/` · 다른 서비스 · `docs/screens` 는 고치지 않는다(필요하면 보고서).
- `git commit` · `push` · `reset` · `checkout --` · `rm -rf` · `.env` 수정 금지. pm2 는 자기 서비스만 restart(전체 재시작 금지).
- 남이 바꾼 파일은 되돌리지 않는다. 다른 기능 폴더의 타입 오류는 무시해도 된다(typecheck SERVICE=x 는 자기 폴더 오류만 실패로 센다).

## 보고(마지막 메시지)
바꾼 파일 · 새 API · pytest 결과(개수) · typecheck · e2e 결과 · 캡처 경로 · 보드와 다른 곳 · 남은 것 · 공용 부품에 필요한 것.

## 결과 (2026-10-12 통합)

7개 서비스 세션이 모두 끝냈다. pytest rq 42 · dss 18 · mi 132 · ca 104 · vp 38 · sp 65 · sc 66(+ storyboard 53 · libs/common), `make contracts-check` · 웹 typecheck · `make web-build` 통과.
수용 기준은 `docs/scenarios/11-content-flow.md` §7(CD-01~09 · 콘텐츠별 API 표).

통합 때 공용 부품에 반영한 것(서비스 세션 요청):
- `Modal`: 딤(`.wm-scrim`)이 셸 본문 폭 규칙(`:where(.sh-content) > :where(*)`)을 받지 않는다 — 페이지 최상위에 두어도 사이드바까지 덮는다. `className` prop(보드마다 다른 그림자).
- `useEscape`: 여러 겹이 떠 있으면 맨 나중에 켜진 겹창 하나만 Esc 를 받는다(팝업 위 셸 시트 · 팝업 안 목록).
- `InlineInput`: `id` · `inputRef` · `onKeyDown` · `inputMode` · `autoFocus` · `required`(비우고 떠나면 원래 값) · `multiline` + `autosize`(글 높이만큼, Ctrl/⌘+Enter 저장).
  Esc 는 저장하지 않고 고치기 전 값으로 되돌린다(전에는 떠나면서 고친 값이 저장되던 버그).
- `ContentDetail`: `shell` prop(셸에 hasTask · onAdd · addable · added · taskContext · accepts 를 넘김 — DSS 의 두 번째 `useShellPage` 우회를 걷어냄) · 제네릭 `onSave: () => Promise<T>` / `savedToast(out: T)`.
- 되돌리기 토스트 조사: `josaRo` (`@/ui` — 「v3으로」 · 「v2로」). 요구사항의 `euro` 도 이것으로 바꿨다.

남은 공용 요청(다음 플랫폼 작업):
- `@/ui` 알약 · 칩 고르기 목록(listbox) — 지금은 기능마다 따로(VP `ChipSelect` · CA `Pick` · SC `wm-menu` · SP `spd-itemsl`).
- `cd-in` 높이 변형(38 · 34 · 32) · `AiButton` 크기 변형 하나 더(업종 칸 padding 10 · 12).
- `ProductPickerDialog`: 모델 검색(`kinds=model`) 옵션 · 행 `data-name`.
- 「새로 만들기 / 작성 중」 기준을 셸에서 하나로(지금은 기능마다 — 이 탭에서 막 만들었으면 새로 만들기).
- 저장 버튼은 막혀도 `aria-disabled`(누르면 이유 토스트)라 Playwright 에서는 `click({ force: true })` 로 누른다 — 의도된 동작.
