# 웹앱 ① 콘텐츠 흐름 구현 — 서비스 세션 공통 지침 (2026-10-08)

이 문서는 서비스 하나를 맡은 코드 에이전트 세션이 웹앱 ① v58 보드를 코드로 옮길 때 따르는 공통 규칙이다.

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`, 맡은 서비스의 `services/<x>/AGENTS.md`
2. `docs/scenarios/11-content-flow.md` — 특히 §1 규칙 · §4 폭 · **§6 Storyboard 허브 · stage 계약**
3. 보드: `docs/screens/webapp1/<보드>.dc.html`(원본 — 인라인 스타일 px · 문구 · 데이터 예시) + `docs/screens/_rendered/webapp1/<보드>.jpg`(그린 결과, Read 로 본다) · `.txt`
   공통 보드: `List` · `Gate` · `Done` · `SBBar` · `SBPopup` · `ContentPopup` · `JsonPopup` · `ProdPicker` · `Stepper` · `TopBar` · `Sidebar`
4. 참고 구현(이미 끝난 것): VP — `services/vp/src/winmate_vp/valuemap.py`(create 가 `get_flow` 로 DSS 를 읽고, finish 가 `push_stage`) ·
   `web/src/features/vp/values/`(ValuesPage · FlowPages.tsx: `ContentListScreen` · `GateScreen` · `FlowBar` · `FlowDoneView`) · `services/vp/tests/test_value_maps.py` 마지막 테스트.

## 이미 있는 공용 부품(고치지 말고 쓴다 — 필요한 게 없으면 보고서에 적는다)
- 백엔드: `winmate_common.flow.get_flow / push_stage / create_flow`. 테스트에서 허브는 `testing.load_service_app("storyboard")` 를 inprocess 에 넣으면 된다.
- 웹 `@/shell`: `ContentListScreen({content, drafts})`(보드 List) · `GateScreen({content, onStart, initialSb})`(보드 Gate · 수정/복제본 포함) ·
  `FlowBar({sbIds, current, note})`(보드 SBBar + SBPopup) · `FlowDoneView({sbId, stageKey, stage, mdAdded, title, sub, onEdit, follow})`(보드 Done + JsonPopup) ·
  `ContentPopup` · `SBPopup` · `useFlow` · `useFlows` · `CONTENT` · `FlowDots` · `whenText`.
- 웹 `@/ui`: `FlowScreen` · `FlowHead` · `AiButton` · `AiBar` · `ByTag` · `KindTag` · `FlowPanel` · `FlowFooter` · `FollowCard`(후속 작업 카드) · `JsonPopup` ·
  `ProductPickerDialog`(보드 ProdPicker) · `Modal` · `Tabs` · `Skeleton` · `ErrorState` · `toast` …(web/src/ui/README.md §6-1)

## 하는 일(서비스마다)
1. **백엔드**: 새 흐름 자원 하나(예: `/v1/mi-flows*` — 기존 경로와 이름이 겹치지 않게, 스키마 이름도 접두어를 붙인다: VP 는 `VM*`, SC 는 `SS*`).
   - 만들기 `POST {sb_id}` → `get_flow(sb_id)` 로 사전 작업 값을 읽어 시작 값을 채운다(없으면 404, 사전 작업 없으면 422 `PREREQUISITE_MISSING`).
   - 고치기(PUT/PATCH, expected_version 409) · AI 추가기능(`ai()` · task `<기능>.<동작>.v1` · confidential=True · 실패하면 결정적 대체 · 결과는 점선 `by: ai-pending` → 수락) ·
   - 저장 `:finish` → `push_stage(sb, key, ref=코드, ver=저장 횟수, res_id=자원 id, title=, value=§6 계약 모양, md=요약 줄, card=팝업 값)` →
     응답 `{stage, summary_md, flow_sync: {md_added, synced} | null}`. `register_item(feature=<코드>, route=편집 경로)`.
   - 사실(수치 · 모델명 · 고객명)을 지어내지 않는다. 근거 없으면 `[확인 필요]` · `[00]` · `[위키 값]` · `[견적 확인]`.
   - mock 응답 `mocks/ai-tools/<task>.json`(보드 예시 문장으로 `when.contains` + default).
   - 테스트 `services/<x>/tests/test_<x>_flow.py` — 허브 연동(만들기 → 고치기 → AI → 저장 → 허브 stages 값 확인)까지.
   - `make test SERVICE=<x>` 전체 통과 · `make contracts SERVICE=<x>` · `make contracts-check`.
2. **웹** `web/src/features/<x>/flow/`(새 폴더):
   - 목록 `/<base>` = `ContentListScreen`(초안 drafts 는 자기 목록 API 로) · 새로 `/<base>/new` = `GateScreen`(`initialSb={?sb}` · `autoStart={?auto === '1'}` — Storyboard 화면의 「만들기」가 `/<base>/new?sb=<id>&auto=1` 로 온다) · 편집 `/<base>/flow/:id`(§6 경로) · 완료 = `FlowDoneView`.
   - 이전 흐름의 목록 · 새로 만들기는 `/<base>/legacy` · `/<base>/legacy/new` 로 옮기고, 이전 화면 안의 `'/<base>'` · `'/<base>/new'` 링크와 이전 e2e 의 `goto` 도 그에 맞게 바꾼다.
     이전 흐름의 다른 경로(`/:id/...`)는 그대로 둔다(제안서 handoff 가 읽는다).
   - 화면은 `useShellPage({section, title, stepper: {steps, current}})`. 스텝바 단계 이름은 보드 Gate META 그대로.
   - **보드를 철저히 따른다**: 칸 폭 · 높이 · 패딩 · 글자 크기 · 둥글기 · 문구를 보드 인라인 스타일 px 그대로. 본문 열은 셸이 1180 으로 맞추니 화면에서 max-width 를 주지 않는다.
     고정 칸은 px, 나머지 `minmax(0, 1fr)`, 작업 화면은 `FlowScreen` 으로 높이를 채우고 패널 안에서만 스크롤. 색은 `var(--wm-*)` 토큰(web/src/ui/tokens.css · ui.css :root).
   - CSS 는 기능 폴더 안 파일(접두어 클래스). `@/ui` · `@/shell` 파일은 고치지 않는다.
3. **e2e** `web/e2e/<x>/<x>-flow.spec.ts`: API 로 Storyboard 를 만들고(아래 도우미) 목록 → Gate → 편집 → AI → 저장 → 완료까지,
   폭을 숫자로 재고(보드 고정 칸) `shot()` 으로 `__screens__/<보드>-new.png` 를 남긴다. `make e2e-feature SERVICE=<x>` 로 돌린다(다른 세션과 동시에 돌 수 있으니 1 worker).
   Storyboard 만들기(내부 전용 경로라 요청 헤더가 필요): `X-Internal-Token: <data/.internal_token>` · `X-Internal-Caller: requirements` 로
   `POST /api/storyboard/v1/flows {name, customer, rq:{ref, ver, value, md}}` → `PUT /api/storyboard/v1/flows/{id}/stages/dss {ref, value, md}` (값 모양은 §6).
   Playwright request 에 헤더를 넣어 부르면 된다(토큰은 `fs.readFileSync('../data/.internal_token')`).
4. **화면 대조**: 캡처를 `docs/screens/_rendered/webapp1/<보드>.jpg` 와 나란히 Read 로 보고 차이를 고친다(폭 · 칸 · 줄바꿈 · 버튼 위치 · 문구). 보드와 다르게 한 곳은 보고서에 「보드와 다름: 무엇 · 왜」.
5. `services/<x>/AGENTS.md` "현재 상태" 맨 위에 「새 흐름(2026-10-08)」 절을 짧게 더한다.

## 하지 말 것
- 맡은 서비스 owns 밖 파일 수정(특히 `web/src/shell` · `web/src/ui` · `libs/common` · `config/` · 다른 서비스). 필요하면 보고서에 적는다.
- `git commit` · `git push` · `git reset` · `rm -rf` · `.env` 수정. pm2 는 자기 서비스만 `ops/node_modules/.bin/pm2 restart <x>`(전체 재시작 금지 — 다른 세션이 쓰는 중).
- 다른 세션이 동시에 같은 작업 트리를 쓴다. 남이 바꾼 파일은 되돌리지 않는다.

## 보고(마지막 메시지)
바꾼 파일 목록 · 새 API · 테스트 결과(개수) · e2e 결과 · 캡처 경로 · 보드와 다른 곳 · 남은 것 · 공용 부품에 필요한 것.
