# B2B 제안서(PR) — 웹 화면

시나리오 `docs/scenarios/10-proposal.md`, 보드 `docs/screens/webapp3/*.dc.html`(PR · PRU · PRS/PRQ/PRX · DnD · OneClick · Layout).
`index.tsx` 가 `feature({ code: 'PR', key: 'proposal', order: 10, home })` 로 셸에 등록한다. 모든 경로는 `/proposal/...`.

## 라우트 ↔ 보드

| 라우트 | 화면(파일) | 보드 |
|---|---|---|
| `/proposal` | 목록 `pages/ListPage` | PR0 |
| `/proposal/new?start=rfp\|works\|reuse&source=` · `?handoff=` · `?link=` · `?sb=&rq=` · `?image_version=` | 시작 방식이 정해지는 순간 만들기 `pages/StartPages#NewPage` | (PR0 → PR1 · PR1F · PR1L · PR1C, 다른 기능 「새 제안서로 시작」) |
| `/proposal/:id` | 지금 있는 단계로 이동 `pages/StartPages#OpenPage` | (사이드바 · 「이어서 작성」) |
| `/proposal/:id/customer` | 고객 · 프로젝트(자동 저장) `pages/CustomerPage` | PR1 |
| `/proposal/:id/rfp` | RFP로 시작 `pages/RfpPage` | PR1F |
| `/proposal/:id/works?check=` | 기존 작업에서 시작 `pages/WorksPage` | PR1L |
| `/proposal/:id/reuse?source=` | 기존 제안서로 시작 `reuse/ReuseStartPage` | PR1C |
| `/proposal/:id/reuse/analysis` · `/:no` | 기준별 분석 · 기준 상세 `reuse/ReuseAnalysisPage` | PRU2 · PRU2F |
| `/proposal/:id/reuse/plan?mode=improve\|borrow` | 활용 계획 `reuse/ReusePlanPage` | PRU3A · PRU3B |
| `/proposal/:id/reuse/summary` | 원본 대비 변경 요약 `reuse/ReuseSummaryPage` | PRU5 |
| `/proposal/:id/type` | 제안서 유형 `pages/TypePage` (+ 셸 딸깍 팝오버) | PR2 · OneClickEarly |
| `/proposal/:id/compose` | 시트 구성(유형별) `pages/ComposePage` | PR3 · PR3SolOpen · PR3Quick · PR3Solution |
| `/proposal/:id/industry` | 업종 레이아웃 `pages/IndustryPage` | PR3I |
| `/proposal/:id/sections/:key` | 섹션 작성 `section/SectionPage` (SectionStep + 드롭 · 반입 띠 · 빠른 요청) | SectionStep · PRS1–8 · PRQ1–5 · PRX1–5 · DnD_MISidebar · DnD_Product · DnD_ProductDropped · DnD_Case · DnD_Solution · OneClickConfirm(`?oneclick=1`) |
| `/proposal/:id/sections/:key?view=compare\|guide\|new_only&sheet=` | 원본 대조 · 흐름 가이드 `reuse/ReuseSectionView` | PRU4 · PRU4B |
| `/proposal/:id/sections/:key/sheets/:sheetId/template` | 템플릿 고르기 `section/TemplatePanel` | PRS1Layout · PRS4Layout · PRS5Layout · PRS7Layout · PRS1LayoutInd · PRS2LayoutInd · PRS5LayoutInd · PRX3LayoutInd |
| `/proposal/:id/sections/:key/imports/:importId` | 사이드바 반입 추출 확인 `section/ExtractPanel` | DnD_MIExtract |
| `/proposal/:id/design` | 디자인 템플릿 `pages/DesignPage` | PR6 |
| `/proposal/:id/result?export=1` | PPTX 생성 결과 `pages/ResultPage` · 내보내기 모달 `pages/ExportModal` | PR7 · PR7X |
| `/proposal/:id/one-click/:jobId` | 딸깍 진행 · 완료 `pages/OneClickPage` | OneClickGen · OneClickDone |
| `/proposal/:id/preview[/:no]?filter=inferred&panel=evidence` | 미리보기 · 시트 편집 `pages/PreviewPage` | PR7P |
| `/proposal/:id/confirm` | 확정 필요 목록 `pages/ConfirmPage` | PR7Q |
| `/proposal/:id/review[/:no]` | 검토 · 코멘트 · 승인 `pages/ReviewPage` | PR7C |
| `/proposal/:id/versions?a=&b=&sheet=&change=` | 버전 · 변경 이력 `pages/VersionsPage` | PR7V |

보드 64개 중 62개를 화면으로 구현했다(UC_PR 유스케이스 맵 · Guide 캔버스 안내는 앱 화면이 아님). 섹션 18개 보드는 SectionStep 한 화면이 유형 · 섹션 키로 바뀐다.

다른 기능에서 들어오는 길: `/proposal/:id/sections/:key?handoff=sho_…|vho_…|hof_…&link=<분석 id>`(반입 1회 + 띠 「실행 취소」),
`/proposal/new?handoff=…` · `?link=mi_…` · `?sb=…&rq=…` · `?image_version=…`(start_mode=handoff → PR1), `/proposal?focus=CM&competitor=`(경쟁 비교를 넣을 제안서 고르기 → 「이어서 작성」이 Why Samsung 섹션).

## 구성

- `api/` — `proposal.ts`(TanStack Query 훅 + 호출, `api.proposal` 생성 타입), `http.ts`(오류 봉투 · `isApiError` · `isMissing` · `errText` · `jobErrText`),
  `jobs.ts`(`useJobEvents` — jobs SSE: status · progress · step · awaiting_input · result · done), `comments.ts`(workspace 코멘트 · 사용자), `types.ts`.
- `components/` — `parts.tsx`(PrPage · Agent · Dock · Prompt · Bar · ErrorBand · NextButton …), `SlideView.tsx`(시트 `display` 를 모양으로 그리는 16:9 슬라이드 ·
  선택 · 미니 툴바 · `fieldsAt`/`valueAt`), `SlideThumb.tsx`, `ResultToolbar.tsx`(PR7 계열 위 막대 + `?export=1`).
- `lib/` — `routes.ts`(R · `normalizeRoute` · `currentRoute`), `catalog.ts`(유형 · 섹션 · 템플릿 · 업종 보드 상수), `useProposalShell.ts`(셸 브레드크럼 · 스텝바 · 딸깍 · 드롭 받는 종류 · 추가),
  `useQuickExport.ts`(PDF/PPTX 바로 받기), `format.ts`.
- `pages/` · `section/` · `reuse/` — 위 표의 화면. 스타일은 `proposal.css`(보드 실측, 색은 `var(--wm-*)` 토큰만).

## 셸 연동

- `useProposalShell({ p, step, oneClick: { from, section }, accepts, acceptsWork, added, onAdd, addable, complete, autoFrom })` → `useShellPage`.
  딸깍 버튼은 1–5단계 화면에만(PR1 · PR1F · PR1L · PR1C · PR2 · PR3 · PR3I · 섹션 · PR6), PR7 계열 · 진행 화면엔 없다(AC-003). 팝오버 내용은 `GET …/one-click/plan`.
- 섹션 화면은 받는 자료(`SectionView.accepts`)를 셸 팝오버 · 사이드바 드래그 대상으로 넘기고, 연결 자료 `sources[].ref` 를 `added` 로 넘겨 「✓ 추가됨」을 보인다.

## 오류 · 동시 편집

- 오류 봉투 `{error: {code, message, details}}` → `errText`. 403 `POLICY_CONFIDENTIAL` → 「기밀 자료라 지금 설정된 모델로는 분석할 수 없어요」.
- 시트 PATCH 는 `If-Match: rev`, 409 `REV_CONFLICT` 면 다시 읽고 알린다. 빠른 요청 422 `QUICK_ACTION_NO_JOB` 은 `details.panel · navigate · prefill` 로 화면 안에서 처리.
- 흐름 차용 403 `BORROW_MODE_CONTENT_HIDDEN` → 흐름 가이드로. 활용 계획 확정 직후(applying) 섹션 422 · 원본 대조 404 는 기다렸다가 다시 읽는다.
- 잡 실패: 딸깍 진행 화면은 오류 띠 + 「딸깍 다시 시도」 · 「돌아가기」, PR7X 는 오류 띠, PR1C/PRU2 는 서버 `status_label` · `intro`.

## e2e (`web/e2e/proposal/`)

```bash
make e2e-feature SERVICE=proposal     # Vite 5210(HMR 끔) · /api 는 게이트웨이 · 1 worker
make typecheck SERVICE=proposal
```

- `flow.spec.ts`(실제 백엔드 · mock 모델) — PR0 → PR1 자동 저장 → PR2 → PR3 → PR3I → 섹션 → 템플릿 고정 → 8섹션 확정 → PR6(HEX 검증) → 생성 → PR7(썸네일 10 · [수치 확정 필요]) → PR7X → PR7P 표 행 PATCH(If-Match).
- `backend.spec.ts`(실제 백엔드) — PR1F TXT RFP 9항목 · 딸깍 진행 → 완료 · PR7Q 확정 · PR7V 저장 · 비교 · PR7C 작성 모드 · 기존 제안서 활용(PR1C → PRU2 → PRU3 → PRU4) · PPTX 내보내기.
- `screens.spec.ts`(**MOCK** — `page.route` 로 보드 예시 값을 덮음, 테스트 이름에 「(MOCK)」) — PR1F · PR1F 403 · PR1L · PR1C · PRU2 · PRU2F · PRU3A/B · PRU4/4B · PRU5 · OneClickGen/Done · PR7Q · PR7C · PR7V · PR1(실제).
- 스크린샷 `__screens__/<보드>.png`(MOCK) · `flow-*.png` · `real-*.png` ↔ `docs/screens/webapp3/<보드>.dc.html`.
- 공유 데이터: 테스트는 자기 제안서를 API 로 만들고 끝나면 지운다(목록이 비어 있다고 가정하지 않음).
- 하네스만의 장치: `isolateBrokenFeatures`(다른 기능 index.tsx 가 500 이면 빈 모듈로 — 셸 eager 등록 보호), `watchCrash`(공유 PC 메모리 부족으로 커널이 탭을 죽이면 새 탭으로 확인),
  `retries: 1`(같은 이유 — 다시 돌아 통과하면 flaky 로 보고).

## 남은 것

- 시트 렌더는 `display` 모양으로 판단한다. `slot_schema.slots[].type · box · label` 을 쓰면 PPTX 배치에 더 가깝게 그릴 수 있다(다음 개선).
- PRU4 시트 제목 「되돌리기」(W 초안 제목)는 서버에 초안 제목 값이 없어 줄(불릿)에만 있다.
- 셸 등록이 다른 기능 하나의 import 오류에 같이 깨짐 → `docs/requests/workspace.md` 요청.
- 활용 계획 확정 직후 적용 전 1–2초(422 · 404)는 웹이 기다려 비켜 둠 → `docs/requests/proposal.md` 요청(선택).
