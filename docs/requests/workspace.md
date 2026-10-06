# workspace(셸 · UI 키트) 요청

## 키맨 색 토큰(보드 COL 팔레트) — requirements · 2026-10-06
- 필요: RQ1 · RQ2 · RQ3 · RQ5 · RQ6 · RQ7B 의 키맨 아바타 · 가중치 막대 · 질문 태그가 보드 `COL` 팔레트(5색)를 쓴다.
  토큰이 없는 두 색(`#5468d8`, `#8b9be6`)을 지금은 `web/src/features/requirements/rq.css` 의 `.rq-root` 지역 변수로 두었다.
  Storyboard · MI(키맨 가중치) 화면도 같은 색을 쓰므로 공용 토큰이 있으면 기능끼리 색이 맞는다.
- 제안: `tokens.css` 에 `--wm-km-0..4-bg` · `--wm-km-0..4-fg` (0 = `--wm-brand`/흰 글자, 1 = `#5468d8`/흰, 2 = `--wm-brand-hero-line`/brand,
  3 = `#8b9be6`/흰, 4 = `--wm-brand-badge`/brand). 키맨 `color_index` 는 requirements 응답에 이미 있다(0..4 순환).
- 선택: 가중치 막대(경계 끌기 · 1% 단위 · 각 ≥ 5)와 − / + 스테퍼를 키트 컴포넌트로 올리면 SB · MI 가 그대로 쓸 수 있다
  (지금 구현: `web/src/features/requirements/components/bits.tsx` 의 `WeightBar`, 규칙 `lib/weights.ts`).
- 상태: 요청

## 브랜드 분할 버튼 · 선택 카드 · Q 상자 — storyboard · 2026-10-06
- 필요: SB1S · SB3R 분할 버튼은 보드 값이 키트 `Segmented` 와 다르다(선택 = 흰 바탕 · **brand 글자 700** · h32 13.5px · 트랙 `--wm-surface-3`,
  SB3R 은 `--wm-line-disabled`). 기획 질의 · 섹션 질의 · 요구 정리 · 내보내기(SB1Q~Q3 · SB3S · SB4U · SB4E)의 **선택 카드**(단일 = 원형 라디오,
  순서 있는 복수 = 파란 원 순번 + 오른쪽 역할 라벨, 선택 = 2px brand 테두리 + 그림자 `0 4px 14px rgba(20,40,160,.10)`, 점선 `직접 입력` 줄)와
  질의 에이전트 표시 **`Q` 상자**(흰 바탕 · brand 테두리 · Manrope 800, 주 버튼 안에서는 흰 테두리)도 키트에 없다.
  지금은 `web/src/features/storyboard/parts.tsx`(`Seg` · `Choice` · `CustomInput` · `Q`) · `sb.css` 에 지역으로 두었다(그림자는 가장 가까운 `--wm-shadow-card-hover`).
- 제안: `Segmented` 에 `tone?: 'neutral' | 'brand'` · `size?: 'sm' | 'md'`, `ChoiceCard({ pressed, kind: 'radio' | 'ordered', order, title, hint, badge, right, onClick })`
  · `ChoiceCustomInput` · `QBadge({ size?: 'sm' | 'md' | 'onPrimary' })`, 토큰 `--wm-shadow-choice`. 질의 화면이 있는 MI · 경쟁사도 같이 쓸 수 있다.
- 상태: 요청

## 제안서 작업 항목에 붙는 알림 — spec · 2026-10-06
- 필요: 06-spec §6.10 · §9.12-95 — 넘긴 Spec 시트 값이 바뀌면 "workspace 알림이 제안서 항목으로" 만들어져야 한다.
  지금 spec 은 `jobs().push_notification(<시트 주인>, {service: 'spec', type: 'spec_link_changed', title, ref: sp_id, route: '/proposal/{pid}/sections/spec', proposal_id})`
  로 시트 주인에게만 보낸다(카탈로그 갱신은 `spec_catalog_changed`).
- 제안: 알림 데이터의 `item: {feature: 'PR', id: <proposal id>}` 를 셸이 읽어 사이드바 그 제안서 항목에 배지 · 알림 목록 링크를 달기.
  제안서 담당자가 시트 주인과 다를 수 있으니 workspace `POST /v1/notifications {item_id, title, route}`(internal) 같은 경로가 있으면 그쪽으로 보내겠다.
- 상태: 요청

## 수량 있는 제품 칩 · 사용자 메아리 말풍선 · 회색 분할 버튼 — image · 2026-10-06
- 필요: IMG2 「등장 제품」 칩은 `Smart Signage QM55C ×3` 처럼 **수량**을 붙이고 `×` 숫자를 눌러 1~9 로 바꾼다(07-image §4.3, 툴팁 「수량 바꾸기」).
  키트 `ProductInput` 은 토큰에 수량이 없어 `web/src/features/image/components.tsx` 의 `ProductChips`(검색은 키트 `searchProducts`)로 대신했다.
  제안: `ProductToken.qty?` + `qtyMax?` 와 버블 안 수량 버튼(onQtyChange). 조감도 · 시나리오 · 제안서 제품 입력도 같은 수량 칩을 쓴다.
- 필요: 모든 IMG 화면 상단의 사용자 입력 **메아리 말풍선**(오른쪽 정렬 · `--wm-surface-3` · r 16/16/4/16 · 14.5px, 「**공간** · 카페 …」)과
  W 말풍선 아래에 작업 카드를 두는 틀(`ChatLine` 은 글만 받는다)이 키트에 없다 → `Echo` · `WSay` 지역 부품.
  제안: `EchoBubble({ head, children })` · `ChatLine` 에 `children` 아래 `body` 슬롯.
- 필요: 보드의 회색 트랙 분할 버튼(선택 = 흰 바탕 · brand 글자 600 · `--wm-elev-1`, h28/h24 — IMG3E 도구 · 보기, IMG3V 맞추는 방법 · 업스케일, IMG4 해상도 · 넣는 방식)
  과 선 · 파랑 채움 분할 버튼(IMG2P 배열 · 설치, IMG2R 강도). storyboard 요청(브랜드 분할 버튼)과 같은 갈래 — `Segmented` 에 `tone` · `size` 가 생기면 바꾸겠다.
- 안내(셸 「내 생성 이미지」 탭): `GET /api/image/v1/images?owner=me&q=&limit=24` 는 **저장한 시안만**(생성 중 타일 제외) `{items: [{id, title, width, height,
  format, bytes, created_at, file_id, thumb_url, …}], total}` 를 준다. 정보 행은 `GET /api/image/v1/images/{id}/info` → `{rows: [{k, v, href?}]}`
  (「사용 이력」 = `Winmate 제안서 1건`). 홈 「대화에 첨부」는 IMG0 의 `onAttach` 가 `/image/new/references?refs=kb:image:…,img:image:…` 로 새 작업을 만든다.
- 상태: 요청(부품) · 완료(안내)

## 판단 모드 칩 · 출처 카드 · 근거 패널 — mi · 2026-10-06
- 필요(03-mi §4.4 · §4.11, 보드 MI2A · MI3S · MIR): 에이전트 판단 모드 칩(`자동` 번개 · `확인 권장` · `묻기` · `고정` 자물쇠, 흐림 상태 포함),
  출처 카드(종류 라벨 · 상태 배지 `원문 일치`/`확인 필요` · 인용문 하이라이트 `<mark>` · 사유 · 동작 버튼 줄), 오른쪽 근거 패널(머리 · 종류 필터 탭 · 선택한 주장 상자 · 카드 목록 · 닫기)이
  키트에 없어 `web/src/features/mi/parts.tsx`(`ModeChip`) · `pages/SourcesView.tsx`(카드 · 패널)에 지역 부품으로 만들었다.
- 제안: `ModeChip({mode: 'auto'|'check'|'ask'|'pin', dim?})` · `SourceCard({kind, status, title, meta, quote: {before, highlight, after}, reason, actions})` ·
  `EvidencePanel({title, sub, filters, selected, onClose, children})`. 경쟁사 · VP · 제안서(PR7Q 수치 찾기)도 같은 출처 카드를 쓸 수 있다. 키트에 생기면 바꾸겠다.
- 상태: 요청

## 스위치 큰 크기(36×22) — competitor · 2026-10-07
- 필요: 보드 CA2 후보 · CA3C 기준 · CA5 익명 스위치(MI2C 와 같은 모양)는 트랙 36×22 · 손잡이 16 이다. `@/ui` `Toggle` 은 28×16 이라
  경쟁사 화면은 같은 모양 스위치를 기능 CSS(토큰만)로 그렸다. `Toggle size="lg"`(36×22, `aria-label` 만 있는 형태) 가 생기면 바꿔 쓰겠다.
- 상태: 요청(선택)

## 셸 밖 휴대폰 업로드 경로 · 제품 입력 머리글 문구 — birdseye · 2026-10-07
- 필요 1(08-birdseye §4.4 · AC20): BE1P QR 주소는 `/m/upload/{token}`(birdseye `POST /v1/birdseyes/{id}/upload-tokens` 응답 `path` · `url`).
  휴대폰에서 셸(사이드바 · 상단바) 없이 열리는 최상위 경로가 필요하다.
  제안: `feature({ bareRoutes: [{ path: '/m/upload/:token', element }] })` 처럼 기능이 셸 밖 경로를 등록하거나, 셸이 `/m/upload/:token` → `/birdseye/m/:token` 으로 넘겨 주기.
  화면은 `web/src/features/birdseye/pages/MobileUploadPage.tsx`(기본 내보내기) 그대로 쓰면 된다. 지금은 셸 안 `/birdseye/m/:token` 으로만 열린다.
- 필요 2(AC23): `ProductInput` 결과 머리가 「"{q}" 검색 결과 · 방향키로 이동, Enter로 추가」로 고정 — BE2 보드는 「"{q}" 검색 결과 · Enter로 추가」,
  포커스 행 오른쪽 「추가 ↵」(이미 넣은 행은 「이미 추가됨」). 제안: `headText?: (q: string) => string` · `rowCta?: (item, added: boolean) => ReactNode` props.
  지금은 BE2 가 같은 동작의 로컬 컴포넌트(`features/birdseye/pages/ProductsPage.tsx` 의 ProductSearch)를 쓴다. 생기면 키트로 바꾼다.
- 상태: 요청

## 검토 요청에 마감일 · 시트별 확인 · 다시 요청(라운드) — proposal · 2026-10-07
- 필요(10-proposal §4.21 PR7C · AC-160~165): 제안서 검토는 workspace `POST /v1/reviews` · `POST /v1/reviews/{id}/decision` · `/v1/comments`(target `proposal:{pid}:sheet:{sheetId}`)로
  돌고 있다. 아래 세 가지가 `Review` 모양에 없어 지금은 proposal 이 자기 문서에 따로 들고 있다(화면은 동작함). 공용으로 있으면 셸 알림 · 다른 기능도 같이 쓸 수 있다.
  1. `ReviewBody.due_date`(YYYY-MM-DD, 선택) → `Review.due_date` — 「마감 10월 8일 (목)」, 셸 알림 「D-1」 정렬.
  2. 검토자별 대상 확인 `PUT /v1/reviews/{id}/checks/{target_ref} {state: ok|need, comment?}` → `Review.checks: [{user_id, target_ref, state, at}]`
     (PR7C 시트 띠의 「확인됨」 점 · 「검토자 2명 중 1명 확인」).
  3. 변경 요청 뒤 다시 요청 `POST /v1/reviews/{id}/resubmit {message?, version_label?}` → 같은 리뷰의 `round` +1, 결정 초기화(이력은 `rounds[]` 에 남김).
     지금은 proposal 이 새 리뷰를 만들어 옛 리뷰를 cancel 한다.
- 알림: 리뷰 생성 · 결정 · 다시 요청 때 검토자/요청자에게 `jobs().push_notification` 같은 셸 알림(`{type: 'review_requested'|'review_decided', item: {feature: 'PR', id}, route}`)을
  workspace 가 내 주면 기능마다 따로 보내지 않아도 된다.
- 상태: 요청(급하지 않음 — proposal 은 자체 보관으로 동작 중)

## 작업 고르기 대화상자 · 읽기 전용 오른쪽 시트 — vp · 2026-10-07
- 필요(05-vp E2 · E3 · §4.3): VP0 `Storyboard에서` · `MI 결과에서` · `이전 가치 제안 복제` 는 "다른 기능의 작업 하나 고르기"(검색 · 목록 · 선택 · 확인)이고,
  SB · MI · 제안서도 같은 모양을 쓴다. VPR(`/vp/rules`)은 여러 화면(VP0 · VP1 · VP2 · VP1Q · VP3L · VPI)에서 여는 **읽기 전용 오른쪽 시트**인데 키트 `Modal` 은 가운데 시트뿐이다.
- 제안: ① `WorkPickerDialog({feature, title, extra?, confirmLabel, onConfirm(item)})` — `GET /api/workspace/v1/items?feature=&q=&owner=all` 목록 · 검색 · 단일 선택(지금 구현:
  `web/src/features/vp/pages/List.tsx` 의 `WorkPicker`, 복제일 때 고객사 입력 칸을 extra 로). ② `Modal variant="side"`(오른쪽에 붙는 높이 100% 시트, 폭 지정 · Esc · 딤 클릭 닫기).
- 지금은: VPR 을 키트 `Modal`(폭 1200) 로 열고, 닫으면 연 화면(`location.state.back`)으로 돌아간다. 키트에 생기면 바꾸겠다.
- 상태: 요청

## [proposal-web] 셸 기능 등록이 다른 기능 하나의 import 오류에 같이 깨짐 — proposal-web · 2026-10-07
- 무엇: `web/src/shell/registry.ts` 의 `import.meta.glob('../features/*/index.tsx', { eager: true })` — 기능 하나의 index.tsx 가 없는 파일을 import 하면
  (다른 세션이 그 기능을 고치는 중, Vite 500) 앱 전체가 빈 화면이 된다. 오늘 scenario · birdseye 작업 중에 몇 번 겪었다.
- 원하는 것: 기능마다 따로 불러오기(lazy `import()` + 오류 경계) — 깨진 기능 경로만 「이 기능을 불러오지 못했어요」, 나머지 기능 · 사이드바는 그대로.
  사이드바 메뉴에 필요한 정보(code · key · order · 이름)는 지금처럼 가볍게 eager 로 두고 화면(routes)만 lazy 여도 된다.
- 지금: proposal e2e 는 하네스에서만 그런 기능 index.tsx 응답(≥500)을 빈 모듈로 바꿔 돈다(`web/e2e/proposal/helpers.ts` 의 `isolateBrokenFeatures`). 제품 동작은 바꾸지 않았다.
- 상태: 요청

## 처리 상태 — workspace · 2026-10-07
- 상태(키맨 색 토큰 · 가중치 막대 — requirements): 완료 — `tokens.css` `--wm-km-{0..4}-bg` · `--wm-km-{0..4}-fg`(보드 COL 그대로) · `kmClass(i)` · `kmColors(i)` · `KeymanAvatar` · `KeymanDot` · `WeightBar({ items: [{id, name, colorIndex, weight}], size, onCommit })`(경계 끌기 1% · 각 ≥ 5 · ←/→, `data-weights`) · `WeightStepper({ value, onStep(±1), label })` · 규칙 `equalWeights` · `stepWeights` · `moveWeightBoundary` · `distributeWeights` · `WEIGHT_MIN`(requirements `lib/weights.ts` 와 같은 결과). 견본 `/_dev/kit` · README §13. `.rq-root` 지역 변수는 이 토큰으로 바꿔도 된다.
- 상태(브랜드 분할 버튼 · 선택 카드 · Q 상자 — storyboard): 완료 — `Segmented` 에 `tone: 'neutral'|'brand'` · `h: 24|28|30|32`(32 = 13.5px · 선택 700) · `variant: 'track'|'line'` · `trackStrong`(SB3R `--wm-line-disabled`) · `ariaLabel` · 항목 `disabled` · `title`.
  `ChoiceCard({ pressed, kind: 'radio'|'ordered'|'check'|'none', order, title, hint, badge, aside(역할 라벨), right, icon, minHeight, weight, children })`(선택 = 2px brand + `--wm-shadow-choice`) · `ChoiceList` · `ChoiceCustomInput` · `QBadge({ size: 'xs'|'sm'|'md'|'lg'|'onPrimary' })`. README §2 · §12.
- 상태(작업 항목 알림 — spec): 완료 — workspace `POST /v1/notifications {item_id, title, route?, type?, message?, ref?, service?, recipients?, exclude_actor?}`(internal) → 그 항목 주인(+ recipients)에게 저장 + jobs 알림 흐름에도. `item: {feature, id}` 를 셸이 읽어 사이드바 그 항목에 읽지 않은 수 · 그룹 점 · 사용자 메뉴(설정 버튼) 알림 목록을 보인다(그 작업물 화면을 열면 읽음).
  spec 은 `push_notification(<시트 주인>, …)` 대신 `ServiceClient("workspace").post("/v1/notifications", json={"item_id": pid, "type": "spec_link_changed", "title": …, "route": f"/proposal/{pid}/sections/spec", "ref": sp_id})` 로 바꾸면 된다(consumes 에 workspace 있음). 계약 contracts/workspace.json.
- 상태(수량 제품 칩 · 메아리 말풍선 · 회색 분할 버튼 — image): 완료 — `ProductToken.qty` · `ProductInput qty qtyMax` · `Bubble({ qty, qtyMax, onQtyChange })`(`×n` 툴팁 `수량 바꾸기`, 1~9 메뉴) · `EchoBubble({ head, children })` · `ChatLine({ children, body })` · `Segmented tone="brand" h={28|24}` · `Segmented variant="line" h={30|26}`(IMG2P · IMG2R). 셸 「내 생성 이미지」 정보 패널은 이제 `GET /api/image/v1/images/{id}/info` 행을 그대로 쓴다(못 받으면 셸 값).
- 상태(판단 모드 칩 · 출처 카드 · 근거 패널 — mi): 완료 — `ModeChip({ mode, dim, children })`(보드 MIR 글 `자동` · `확인 권장` · `선택 필요` · `고정`, 다른 글은 children) · `SourceCard({ n, kind, kindIcon, status: 'ok'|'warn', title, meta, quote: {before, highlight, after} | string, reason, flag, actions: [{label, icon, onClick|href, tone}] })` · `EvidencePanel({ title, sub, filters: {items, value, onChange}, selected: {text, meta}, onClose, footer })`(폭 420, `--wm-shadow-panel`). README §14.
- 상태(스위치 큰 크기 — competitor): 완료 — `Toggle size="lg"`(트랙 36×22 · 손잡이 16, `label` 만 주는 형태) · `disabled` · `title`.
- 상태(셸 밖 휴대폰 업로드 경로 · 제품 입력 머리글 — birdseye): 완료 — `FeatureModule.publicRoutes`(사이드바 · 상단바 · 로그인 확인 없이, 401 이어도 로그인 화면으로 가지 않음). birdseye `index.tsx` 에 `publicRoutes: [{ path: '/m/upload/:token', element: L(<MobileUploadPage />) }]` 한 줄을 더했다(셸 안 `/birdseye/m/:token` 도 그대로).
  `ProductInput headText={(q) => \`"${q}" 검색 결과 · Enter로 추가\`}` · `rowCta={(item, added, active) => …}`(기본 = 포커스 행 `추가 ↵` / `이미 추가됨`). MobileUploadPage 의 createPortal 덮개는 이제 없어도 된다(셸 밖에서 그려짐).
- 상태(검토 마감일 · 시트별 확인 · 다시 요청 — proposal): 완료 — `ReviewBody.due_date`(YYYY-MM-DD) · `item_id` · `version_label` → `Review.due_date` · `round` · `checks[]` · `rounds[]` · `requested_at`. `PUT|DELETE /v1/reviews/{id}/checks/{target_ref}`(검토자만, `{state: ok|need, comment?}`) · `POST /v1/reviews/{id}/resubmit {message?, version_label?, due_date?}`(요청자만, round +1 · 결정 · 확인 초기화, 지난 라운드는 rounds[]) · `PATCH /v1/reviews/{id}`(마감일 바꾸기 · `clear_due_date`) · `GET /v1/reviews?item_id=`.
  알림은 workspace 가 낸다: 요청 → 검토자 `review_requested`, 결정 → 요청자 `review_decided`(`data.decision`), 다시 요청 → 검토자 `review_resubmitted` — `item: {feature: 'PR', id}`(item_id 가 없으면 target `proposal:<pid>:…` 의 pid 가 색인에 있으면 그것). 예전 `review_approve` · `review_request_changes` 종류 이름은 `review_decided` 로 바뀌었다.
- 상태(작업 고르기 대화상자 · 읽기 전용 오른쪽 시트 — vp): 완료 — `WorkPickerDialog({ feature, title, confirmLabel, onConfirm(item), onClose, extra, canConfirm, disabledReason, exclude, owner })`(workspace items 검색 · 단일 선택 · ↑↓ · Enter · 두 번 누르기, onConfirm 예외는 대화상자 안 메시지) · `fetchWorkItems` · `Modal variant="side"` · `SideSheet`(폭 기본 560, 높이 100%, Esc · 딤 클릭). README §4 · §15.
- 상태([proposal-web] 기능 하나의 import 오류에 셸 전체가 깨짐): 완료 — `registry.ts` 가 기능마다 따로 불러온다(non-eager glob + `Promise.allSettled`, main.tsx 가 처음 그리기 전에 기다림). import 오류(Vite 500 · 문법 · 빈 모듈 `export default null`)면 그 기능 경로만 「이 기능을 불러오지 못했어요」(다시 시도 · 홈으로 · 자세한 오류),
  그리다 오류면 기능 경로마다 오류 경계가 본문에만 「화면을 그리다 문제가 생겼어요」. 사이드바 · 홈은 셸 카탈로그로 그대로. `web/e2e/proposal/helpers.ts` 의 `isolateBrokenFeatures` 는 이제 없어도 된다(있어도 무해 — 빈 모듈은 그 기능만 오류 화면).
