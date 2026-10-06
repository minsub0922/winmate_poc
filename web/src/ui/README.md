# Winmate UI 키트 · 셸 API

기능 화면(`web/src/features/<기능>/`)이 쓰는 공통 부품과 셸 연결 방법. 디자인 원본은 `docs/scenarios/00-shell.md` §2(토큰 · 컴포넌트) · §5(셸 화면) · §7.5(셸 ↔ 기능 계약).

- 소유: workspace 세션(`config/services.yaml` → `web/src/ui/**` · `web/src/shell/**`). 필요한 부품 · 필드가 없으면 `docs/requests/workspace.md` 에 적는다.
- 가져오기: 부품은 `import { … } from '@/ui'`, 셸 연결은 `import { … } from '@/shell'`(옛 경로 `@/shell/feature` · `@/shell/ShellContext` · `@/shell/types` 도 그대로 된다).
- 공개 API 는 **더하기만** 한다(이름 바꾸기 · 지우기 없음).
- 살아 있는 견본: 개발 빌드에서 `/_dev/kit`(부품) · `/_dev/shell`(팝오버 · 시트 · 끌어서 추가 · 스텝바). 아래 [개발 화면](#개발-화면) 참고.

## 0. 지켜야 할 것

| 규칙 | 방법 |
|---|---|
| 색 · 그림자 · 글꼴은 토큰만 | `var(--wm-*)`. hex 를 직접 쓰지 않는다(§2). |
| 비활성 버튼은 이유를 `title` 로 | `<Button disabled disabledReason="진행 중인 작업이 없습니다">` (§8.15 X-03) |
| 바깥 링크는 새 탭 + `rel="noopener noreferrer"` | `ButtonLink` · `ExternalLink` 가 `http(s)://` 주소면 자동으로 붙인다(L-05). |
| 이미지는 같은 출처만 | `Img` 는 바깥 주소(`https://images.samsung.com/…`)를 그리지 않고 빈 칸을 그린다(L-03, 사내망 오프라인). kb 이미지는 `/api/kb/v1/images/{id}/thumb · /file`. |
| 사실은 지어내지 않는다 | 값이 없으면 `[확인 필요]`(AGENTS §2). |
| 숫자는 Manrope | `className="wm-num"` 또는 부품이 알아서(`Count` · `MatchChip` · 탭 숫자). |
| 보조 클래스 | `wm-row` · `wm-col` · `wm-small` · `wm-muted` · `wm-subtle` · `wm-ellipsis` · `wm-sr-only` · `wm-divider` · `wm-num` |

## 1. 토큰 (`tokens.css`)

글꼴은 로컬 번들(`@fontsource/noto-sans-kr` · `@fontsource/manrope`) — CDN 없음. `@/ui` 를 가져오면 `tokens.css` · `ui.css` 가 함께 들어온다.

| 묶음 | 토큰 |
|---|---|
| 브랜드 | `--wm-brand`(#1428a0) · `-hover` · `-50`(#eaeefb, 선택 바탕) · `-25` · `-hero` · `-hero-hover` · `-hero-line` · `-badge` · `-line` · `-sel-line`(#b8c3ee) · `-on-dark` |
| 글자 | `--wm-text`(#121417) · `-text-2` · `-text-muted` · `-text-subtle` · `-text-disabled` · `--wm-placeholder` |
| 바탕 · 선 | `--wm-bg` · `--wm-surface` · `-surface-2` · `-surface-3` · `--wm-line`(#e2e5ea) · `-line-hover` · `-line-soft` · `-line-tile` · `-line-disabled` · `-line-step`(#d5d9e0) · `-line-dashed` |
| 어두운 면 | `--wm-dark` · `--wm-dark-divider` · `--wm-dark-text-2` · `--wm-scrim` · `--wm-photo-badge` · `--wm-grip-chip` |
| 상태 | `--wm-ok`/`-ok-bg`/`-ok-bg-2`/`-ok-line` · `--wm-warn`/`-warn-bg`/`-warn-line` · `--wm-danger`/`-danger-bg`/`-danger-line`(보드에 없음 Q-UI-1) · `--wm-ai`/`-ai-bg`(AI 추론 배지) |
| 그림자 | `--wm-shadow-popover` · `-sheet` · `-dialog` · `-ghost` · `-dropdown` · `-composer` · `-card-hover` · `-card-new` · `--wm-ring` · `-ring-soft` · `-ring-drop` · `--wm-elev-1` · `--wm-shadow-choice`(선택 카드) · `--wm-shadow-panel`(오른쪽 근거 패널) · `--wm-shadow-side`(오른쪽 시트) |
| 키맨 색(보드 COL) | `--wm-km-{0..4}-bg` · `--wm-km-{0..4}-fg` — 0 brand/흰 · 1 `#5468d8`/흰 · 2 `--wm-brand-hero-line`/brand · 3 `#8b9be6`/흰 · 4 `--wm-brand-badge`/brand. 키맨 `color_index`(0..4 순환) → `kmClass(i)` · `kmColors(i)` |
| 글꼴 | `--wm-font`(Noto Sans KR) · `--wm-font-num`(Manrope) |
| 배치 | `--wm-sidebar-w`(260) · `--wm-topbar-h`(64) · `--wm-stepper-h`(56) · `--wm-content-w`(800) |
| 겹침 | `--wm-z-stepper` 20 · `-topbar` 30 · `-scrim` 40 · `-sheet` 41 · `-toast` 50 · `-ghost` 60 |
| 움직임 | `--wm-ease-out` |

## 2. 컨트롤 (`controls.tsx`)

### `Button`
보드 버튼(§2.8). `forwardRef` 로 `<button>` 속성을 모두 받는다.

| prop | 타입 | 설명 |
|---|---|---|
| `variant` | `'primary' \| 'secondary' \| 'dark' \| 'outline' \| 'ghost' \| 'danger' \| 'soft'` | 기본 `secondary`(흰 바탕 · 회색 선) |
| `h` | `26 \| 28 \| 32 \| 34 \| 36 \| 38 \| 40 \| 44 \| 48` | 보드 높이 그대로(우선) |
| `size` | `'xs' \| 'sm' \| 'md' \| 'lg'` | 옛 크기(26 · 32 · 38 · 44). `h` 가 있으면 무시 |
| `disabledReason` | string | 비활성일 때 `title` |
| `loading` | boolean | 스피너 + 비활성 |
| `icon` · `iconRight` | ReactNode | 앞 · 뒤 아이콘 |
| `block` · `grow` | boolean | 폭 100% · `flex: 1` |
| `brandText` | boolean | 흰 버튼에 brand 글자(`+ 추가` · `실행 취소`) |

```tsx
<Button h={44} variant="primary" grow onClick={make}>Spec 시트 만들기</Button>
<Button h={32} disabled={!task} disabledReason="진행 중인 작업이 없습니다">현재 작업에 추가</Button>
<Button h={38} variant="dark" icon={<BoltIcon size={13} />}>딸깍, 완성하기</Button>
```

### `ButtonLink` · `ExternalLink`
버튼 모양 링크 / 글 링크. `http(s)://` 이면 `target="_blank" rel="noopener noreferrer"` 자동(`external` 로 강제 가능). `ButtonLink` 는 `variant` · `h`(기본 38) · `block` · `grow` · `icon` · `iconRight` · `brandText`, `ExternalLink` 는 `arrow`(뒤 `↗`).

```tsx
<ButtonLink h={28} href={caseUrl}>원문 열기 ↗</ButtonLink>
<ExternalLink href={pdpUrl} arrow>samsung.com 제품 페이지</ExternalLink>
```

### `IconButton` · `CloseButton`
`IconButton({ label, size = 32 | 34, bordered, children, ...button })` — `label` 이 `aria-label`·`title`(사각 선은 `bordered`). `CloseButton({ label = '닫기', size = 32 | 34, onClick })` — X 아이콘.

### `ItemAddButton`
팝오버 행의 `+ 추가` 버튼(§2.8 AddButton). `state`: `'add'`(+ 추가) · `'sel'`(✓ 선택, brand 바탕) · `'added'`(✓ 추가됨, 비활성) · `'off'`(비활성). 접근 이름은 `추가 {name}` / `선택 해제 {name}`.

```tsx
<ItemAddButton state={inTray ? 'sel' : 'add'} name="QM55C" onToggle={toggle} offReason="진행 중인 작업이 없어 추가할 수 없습니다" />
```

### `Field` · `Input` · `TextArea` · `Select`
`Field({ label, hint, extra, children })` 는 `<label>` 묶음. `Input`(`size: 'sm' | 'md'`) · `TextArea` 는 `forwardRef`. `Select<T>({ value, onChange, options: Array<{ value: T; label }> })`.

```tsx
<Field label="고객사" hint="회사 이름 그대로"><Input value={v} onChange={(e) => setV(e.target.value)} /></Field>
```

### `SearchField`
h38 r10 돋보기 입력(§2.8). 라벨은 시각적으로 숨김(접근 이름).

| prop | 설명 |
|---|---|
| `value` · `onChange(v)` | 값 |
| `label` | 접근 이름(기본 `검색`) |
| `tone` | `'gray'`(팝오버, 기본) · `'white'`(작업 목록) |
| `width` · `clearable` · `autoFocus` · `onEnter` · `onKeyDown` · `inputRef` · `id` · `placeholder` | |

```tsx
<SearchField value={q} onChange={setQ} label="요구사항 검색" tone="white" width={280} clearable />
```

### `Chip` (= `FilterChip`)
필터 · 업종 칩. `onClick` 이 있으면 `<button aria-pressed>`, 없으면 `<span>`. props: `on` · `tight` · `size: 'md' | 'lg'` · `count` · `caret`(▾ 메뉴) · `disabled` · `title` · `aria-haspopup` · `aria-expanded`.

```tsx
<Chip on={industry === 'retail'} onClick={() => setIndustry('retail')}>리테일</Chip>
<Chip caret aria-haspopup="menu" aria-expanded={open} onClick={toggle}>업종: 호텔</Chip>
```

### `Tabs`
밑줄 탭(§2.8). `role=tablist`(+`ariaLabel`) · `role=tab` · `aria-selected` · 좌우 화살표로 이동.

| prop | 설명 |
|---|---|
| `value` · `onChange` · `items: TabItem[]` | `TabItem = { value, label, count?, disabled?, id? }` |
| `variant` | `'pop'`(h36 12.5px) · `'sheet'`(h52 13.5px) · 없음(h40 13px) |
| `ariaLabel` · `bare` · `className` | |

```tsx
<Tabs ariaLabel="이미지 출처" variant="pop" value={tab} onChange={setTab}
  items={[{ value: 'all', label: '전체', count: 6 }, { value: 'official', label: '제품 이미지', count: 1 }]} />
```

### `Segmented` · `Toggle` · `Spinner`
`Segmented<T>({ value, onChange, items: { value, label, disabled?, title? }[], tone?, h?, variant?, trackStrong?, ariaLabel?, className? })` — 붙은 버튼 묶음에서 하나 고르기(`aria-pressed`, 묶음은 `role="group"`).

| prop | 값 | 보드 |
|---|---|---|
| `tone` | `'neutral'`(선택 글자 `--wm-text`, 기본) · `'brand'`(선택 글자 brand) | SB1S · SB3R · IMG |
| `h` | track: `30`(기본 12.5px) · `32`(13.5px, 선택 700) · `28`(12.5px) · `24`(12px) — 28 · 24 는 꺼진 글자 `--wm-text-2` 500 · 선택 600 / line: `30`(기본) · `26`(폭 30) | SB1S h32 · IMG3E 도구 · 보기 h28 · IMG3V h24 · IMG2R 강도 h26 |
| `variant` | `'track'`(회색 트랙 + 흰 선택 + `--wm-elev-1`, 기본) · `'line'`(선으로 나눈 묶음 + 선택 파랑 채움) | IMG2P 배열 · 설치 · IMG2R 강도 |
| `trackStrong` | 트랙 바탕 `--wm-line-disabled` | SB3R |

```tsx
<Segmented tone="brand" h={32} ariaLabel="제안 방향" value={v} onChange={setV} items={[{ value: 'concept', label: '컨셉 제안' }, { value: 'pitch', label: '공통 Pitch deck' }]} />
<Segmented tone="brand" h={28} ariaLabel="보기" value={view} onChange={setView} items={[{ value: 'edit', label: '편집' }, { value: 'compare', label: '전/후 비교' }]} />
<Segmented variant="line" h={26} ariaLabel="강도" value={lv} onChange={setLv} items={['1', '2', '3'].map((x) => ({ value: x, label: x }))} />
```

`Toggle({ checked, onChange, children | label, size?: 'md' | 'lg', disabled?, title? })` — `role="switch"` 스위치. `md` 트랙 28×16(`출처 확인된 이미지만`), `lg` 트랙 36×22 · 손잡이 16(CA2 후보 · CA3C 기준 · CA5 익명 · MI2C — 글 없이 `label` 만 주는 형태가 보통).

```tsx
<Toggle size="lg" checked={c.on} onChange={(v) => pick(c.id, v)} label={`${c.name} 포함`} />
```

`Spinner({ label = '불러오는 중' })`.

### `cx`
`cx('a', cond && 'b')` — 거짓 값을 뺀 클래스 이음.

## 3. 표시 (`display.tsx`)

| 부품 | props | 쓰는 곳 · 예 |
|---|---|---|
| `Tag` | `tone?: 'brand' \| 'neutral' \| 'ok' \| 'warn' \| 'danger'`, `title` | 사례 태그 `유통/요식 · DT` |
| `NeutralTag` | `children`, `title` | 회색 제품 칩 `MagicINFO Player` |
| `Badge` | `tone: BadgeTone`, `title`, `style` | `brand`(삼성 공식) · `brand-soft` · `brandline`(대표 이미지 `1 / 8 · 정면 · 삼성 공식`) · `dark`(제목에 명시) · `darksm` · `dashed`(용도 일치 · …) · `photo`(사진 위) · `product` · `new` · `start`(여기서 시작) · `core`(핵심 기능) · `ok` · `warn` · `ai` |
| `Count` (= `CountPill`) | `n` | 사이드바 개수 알약 |
| `KeyChip` | `children` | 시트 핵심 칩 `4K UHD` |
| `CheckChip` | `children` | 체크 칩(딸깍 `확정된 내용`) |
| `MatchChip` | `label`, `n`, `on`, `onClick` | `모델 일치 0` · `용도 일치 3`(on = 검정) |
| `TrayChip` | `label`, `onRemove`, `removeLabel = '선택 해제'` | 팝오버 아래 선택 트레이 |
| `MiniChip` | `tone?: 'gray' \| 'line' \| 'pill'` | 기둥 항목 · 기기 관리 칩 |
| `SourceBadge` | `kind: 'user' \| 'file' \| 'kb' \| 'ai' \| 'web' \| 'warn'`, `title` | 값 출처 배지(KB · AI 추론 · 확인 필요) |
| `StatusBadge` | `tone?: 'neutral' \| 'brand' \| 'ok' \| 'warn' \| 'danger' \| 'dark'`, `icon?: 'check' \| 'spin' \| 'refresh' \| 'warn' \| ReactNode`, `size?: 'md' \| 'lg'` | 작업 상태 알약 `진행 중` · `업데이트 필요` |
| `Avatar` | `initial`, `size = 32`, `title` | 사이드바 사용자 |
| `InfoBox` | `title`, `sub`, `action`, `children`, `style` | 시트 `CMS — MagicINFO · VXT 지원` + `MagicINFO 상세 →` |
| `MetaRows` | `rows: MetaRow[]`, `variant?: 'popover' \| 'sheet'` | 키-값 표. `MetaRow = { k, v, href?, title? }` · 행마다 `data-key={k}` |
| `Notice` | `tone?: 'info' \| 'warn' \| 'ok' \| 'danger'`, `icon` | 한 줄 안내 |
| `Empty` | `title`, `children`, `action`, `size?: 'md' \| 'sm'` | 빈 상태 |
| `ErrorState` | `message`, `onRetry` | 오류 + `다시 시도` |
| `Progress` | `value`(0–100) | 진행 막대(`role=progressbar`) |
| `Skeleton` | `w = '100%'`, `h = 16`, `r = 8`, `style` | 불러오는 중 자리 |
| `Banner` | `tone?: 'done' \| 'info' \| 'ok' \| 'warn' \| 'danger'`, `title`, `sub`, `action`, `onUndo`, `undoLabel = '실행 취소'`, `icon` | 화면 안 결과 알림(토스트 대신, Q-UI-2) |

```tsx
<MetaRows variant="sheet" rows={[
  { k: '출처 페이지', v: 'samsung.com · LH55QMCEBGCXKR', href: pdp },
  { k: '사용 조건', v: '삼성전자 저작물 · 대외 사용 범위 확인 필요' },
]} />
<Banner title="「QM65C」" sub="추가됨 · 카운터 · 메뉴보드 시트에 배치됨" onUndo={undo} />
<StatusBadge tone="brand" icon="spin">확인 중</StatusBadge>
```

## 4. 겹창 (`overlay.tsx`)

### `Modal`
| prop | 설명 |
|---|---|
| `open` · `onClose` | Esc · 딤 클릭(`closeOnScrim`, 기본 true)으로 닫힘 |
| `title` · `ariaLabel` | 머리 제목 / 접근 이름 |
| `variant` | `'sheet'`(r18, 기본) · `'dialog'`(작은 확인창) · `'side'`(오른쪽에 붙는 높이 100% 시트 — 왼쪽 모서리만 r18, 밀려 들어옴) |
| `width = 720` · `height` · `footer` · `bodyStyle` | `side` 는 `width` 가 시트 폭(높이는 언제나 100%) |

포커스는 창 안에 갇히고(`useFocusTrap`), 닫으면 연 요소로 돌아간다.

### `SideSheet`
읽기 전용 오른쪽 시트(VPR 라우팅 규칙 · 상세 보기) — `Modal variant="side"` 와 같고 폭 기본 560. Esc · 딤 클릭 · 닫기 버튼.

```tsx
<SideSheet open={open} onClose={() => nav(loc.state?.back ?? '/vp')} title="에이전트 라우팅 규칙" width={880}><RulesSheet /></SideSheet>
```

### `ConfirmDialog` · `useConfirm`
```tsx
const { confirm, dialog } = useConfirm();
// …
if (await confirm({ title: '이 작업을 지울까요?', message: '지운 작업은 되돌릴 수 없어요.', tone: 'danger', confirmLabel: '지우기' })) remove();
return <>{/* 화면 */}{dialog}</>;
```
`ConfirmOptions = { title, message?, confirmLabel = '확인', cancelLabel = '취소', tone?: 'primary' | 'dark' | 'danger' }`. 직접 쓰려면 `<ConfirmDialog open busy onConfirm onCancel … />`.

### `toast` · `ToastHost`
`toast(message, { action?: { label, onClick }, duration = 3200 })` — 화면을 떠나는 알림에만(보드에 없음, Q-UI-2). `ToastHost` 는 셸 Layout 에 이미 있다.

### `useFocusTrap(ref, active, { initialFocus?, restoreFocus? })` · `useEscape(onEscape, enabled)` · `focusablesIn(root)`
직접 만든 겹창에 쓴다. Esc 는 끌기 취소 → 시트 → 팝오버 순서로 먼저 잡은 쪽이 처리한다.

## 5. 미디어 (`media.tsx`)

### `Img`
`{ src, alt, fit = 'cover' | 'contain', focal?: {x, y}, position?, emptyText?, className?, style? }` — 같은 출처가 아니거나 못 불러오면 빈 칸(`wm-photo-empty`). `focal` 은 `object-position`(0–1).

### `ImageTile`
이미지 검색 · 시트 갤러리 타일. 본 버튼(`.wm-tile`, `aria-pressed` = 포커스)과 체크 단추(`.wm-tile__check`, 선택)가 따로 있다. 스페이스 = 선택 전환.

| prop | 설명 |
|---|---|
| `src` · `alt` · `title` · `meta` | 이미지 · 제목 · 아래 줄(`도입사례 · 1340×820 · samsung.com`) |
| `kind` | `{ label: '제품' \| '도입사례', tone: 'product' \| 'photo' \| 'dark' }` 왼쪽 위 배지 |
| `fit` · `focal` · `imgHeight = 100` · `compact` | |
| `focused` · `onClick` | 정보 패널 대상 |
| `selected` · `selectable` · `onSelectToggle` | 작업에 넣을 선택(체크 원) |
| `grip` · `dragProps` · `dragging` | 끌기(`useDragSource` 결과를 `dragProps` 로) |
| `ariaLabel` · `className` | |

### `ImageCard`
`{ src, title, kind, source, meta, fit, focal, onClick, selected }` — 간단한 이미지 카드(`ImageTile` 감싼 것).

### `PhotoBadge`
사진 위 어두운 배지(`도입사례 사진 · 3장`).

### `CaseCard`
유관 사례 카드(§5.6.2): 큰 사진 + 작은 사진 2 · 태그 · 제목 · 날짜 · 요약 · 제품 칩 · URL · 출처 주석 · `원문 열기`.

| prop | 설명 |
|---|---|
| `title` · `date` · `tag` | |
| `url` · `urlDisplay` | 원문 주소(없으면 링크 · `원문 열기` 숨김) |
| `summary` · `quote` | 요약 2줄. 요약이 없으면 `quote` 를 “ ”로 감싸 보인다(kb G-CASE-1, `data-summary="quote"`) |
| `products` · `matchTerms` | 제품 칩 · `일치 · …` |
| `photos: CaseCardPhoto[]` · `photoCount` | `{ src, alt, focal }` 최대 3 · 배지 장수 |
| `action` · `selected` · `grip` · `dragging` · `dragProps` | 추가 버튼 자리 · 선택 · 끌기 |

### `CaseRow`
시트 안 사례 행(§5.8.7 · §5.9.3): `{ title, date, url, urlDisplay, summary, quote, usedLine, badge, photo, size: 'product' | 'solution' }`.

```tsx
<CaseRow title={c.title} date={formatDate(c.date)} url={c.url} urlDisplay={c.url_display} summary={c.summary} quote={c.quote}
  badge={<Badge tone="dashed">용도 일치 · 매장 사이니지</Badge>} photo={{ src: imageSrc(p), alt: imageAlt(p, c.title) }} />
```

`isSameOrigin(src)` · `focalCss(focal, fallback)` 도 내보낸다.

## 6. 화면 뼈대 (`page.tsx`)

| 부품 | props | 설명 |
|---|---|---|
| `PageHeader` | `title`, `desc`, `actions`, `level?: 1 \| 2` | 화면 머리(h1) |
| `NewButton` | `to` 또는 `onClick`, `h?: 44 \| 48` | `+ 새 요구사항` |
| `FilterTabs<T>` | `value`, `onChange`, `items: FilterTab[]`(`{ value, label, count? }`), `ariaLabel = '상태'` | 작업 목록 상태 탭 |
| `ListToolbar` | `left`, `search?: { value, onChange, placeholder?, label?, width? }`, `right` | 목록 도구 줄 |
| `DataTable<R>` | `columns: DataColumn<R>[]`(`{ key, label, width, render, align? }`), `rows`, `rowKey`, `loading`, `empty`, `onRowClick`, `rowHeight` | 표 카드 |
| `TitleCell` | `title`, `sub`, `to` | 표 제목 칸 |
| `RowAction` | `to`, `primary`, `chevron` | 행 끝 `열기` · `이어서` |
| `ListPage` | `title`, `desc`, `action`, `toolbar`, `banner`, `table`, `children`, `footer` | 작업 목록 화면 틀 |
| `Section` | `title`, `desc`, `actions`, `flat`, `id`, `style` | 섹션 카드 |
| `Composer` | `title`, `meta`, `headRight`, `children`, `actions`, `footLeft`, `wrap = true`, `width = 800` | 하단 입력 카드 |
| `ChatLine` | `children`, `body?` | 어시스턴트 말 줄(W 로고). `body` 를 주면 글 아래(간격 12)에 작업 영역(카드 · 표 · 버튼 줄) |
| `EchoBubble` | `head?`, `children` | 사용자 입력 메아리 말풍선(오른쪽 · `--wm-surface-3` · r 16/16/4/16 · 14.5px · 최대 560) — `head` 굵게 + ` · ` |
| `ContentColumn` | `width = 800`, `gap = 22` | 가운데 본문 열 |
| `ChipRow` | `label`, `desc`, `items: { key, label, count?, to?, onClick? }[]` | `다른 곳에서 시작` 칩 줄 |

```tsx
<ListPage title="고객 요구사항" action={<NewButton to="new">새 요구사항</NewButton>}
  toolbar={<ListToolbar left={<FilterTabs value={f} onChange={setF} items={tabs} />} search={{ value: q, onChange: setQ, label: '요구사항 검색' }} />}
  table={<DataTable rowKey={(r) => r.id} rows={rows} columns={cols} />} />
```
작업 목록은 보통 셸의 [`WorkListPage`](#worklistpage)로 충분하다.

```tsx
<EchoBubble head="공간">카페 · 매장 메뉴보드 3면, 아침 시간대</EchoBubble>
<ChatLine body={<ShotGrid shots={shots} />}>공간과 제품을 넣어 시안 4장을 만들었어요.</ChatLine>
```

## 7. 끌어서 추가 (`dnd.tsx`)

- 끄는 것: 셸 팝오버 항목(제품 · 솔루션 · 이미지 · 사례)과 사이드바 작업 항목. 셸이 붙인다.
- 놓는 곳: 기능 화면이 `DropZone` 또는 `useDropTarget` 으로 만든다. **화면은 `useShellPage({ accepts: [...] })` 로 받는 유형을 알려야** 손잡이가 붙는다.
- 데이터: MIME `application/x-winmate`(= `DRAG_MIME`) JSON `DragPayload`.

```ts
type DragType = 'product' | 'solution' | 'image' | 'case' | 'work_item';
interface DragPayload { type: DragType; ref: string; label: string; sub: string; feature?: string; icon?: string }
// 예: { type: 'product', ref: 'kb:model:mdl_LH65QMCEBGCXKR', label: 'QM65C', sub: '제품 · 단독형 UHD M 시리즈 65"' }
//     { type: 'work_item', ref: 'ws:item:mi_a', label: 'A 커피 …', sub: '사이드바 · Market Intelligence', feature: 'MI' }
```

### `DropZone`
대기(h40 점선 + 받는 유형 칩) → 끄는 중(h76 강조 `여기에 놓아 「{label}」 추가`) → 놓은 뒤(`「{label}」 추가됨 · {설명}` + `실행 취소`). `data-drop-state` = `idle | dragging | over | dropped`, `aria-label="끌어 놓는 영역"`.

| prop | 설명 |
|---|---|
| `accept: DragType[]` | 받는 유형 |
| `acceptWork?: string[]` | `work_item` 일 때 받는 기능 코드(`['MI']`) |
| `onDrop(p)` | 성공이면 아무것도 / `true` / `{ note }` 를 돌려준다. `false` · 예외 = 실패 |
| `onUndo?(p)` | 있으면 `실행 취소` 버튼 |
| `idleText` · `chipLabels` · `workLabel` · `dragTitle(p)` · `dragSub(p)` · `droppedNote(p)` · `disabled` · `className` · `style` | 글 바꾸기 |

```tsx
useShellPage({ section: '공간 조감도 생성', title, accepts: ['product', 'image'], onAdd, added });
<DropZone accept={['product', 'image']} onDrop={async (p) => { await place(p.ref); return { note: '카운터 · 메뉴보드 시트에 배치됨' }; }}
  onUndo={(p) => unplace(p.ref)} />
```
`onDrop` 이 성공하면 셸이 그 팝오버 항목을 `✓ 추가됨` 으로 바꾼다(`onItemDropped`). 끄는 중 `Esc` 는 취소(드롭 없음).

### `useDropTarget(options)`
자기 모양을 쓰려면: `const t = useDropTarget({ accept, acceptWork, onDrop, disabled }); <div {...t.props} data-state={t.state}>`. 돌려주는 값: `state` · `props` · `dragging` · `over` · `busy` · `active`(지금 끄는 것) · `dropped` · `clearDropped()`.

### 그 밖
- `useDragSource(payload | null)` — 끄는 쪽 props(`draggable` · `onDragStart` · `onDragEnd`). 셸 밖에서 새 원천을 만들 때.
- `useActiveDrag()` · `getActiveDrag()` — 지금 끄는 항목. `cancelActiveDrag()` · `readDragPayload(e)` · `onItemDropped(fn)` · `notifyDropped(p)`.
- `DragGhost` · `DragGhostLayer`(셸 Layout 에 있음) · `DragHandle` · `DRAG_TYPE_ICON` · `DRAG_TYPE_LABEL`.
- 파일 올리기: `Dropzone`(= `FileDropzone`) `{ onFiles(files), accept, multiple = true, title, hint, children, disabled }` — 클릭 · 엔터 · 파일 끌어 놓기.

## 8. 제품 입력창 (`ProductInput.tsx`)

§5.10. 입력하면 결과 패널이 입력창 **위로** 열리고(150ms 디바운스), 고르면 버블이 된다. 조감도 · 시나리오 · Spec 시트 · 제안서가 같은 부품을 쓴다.

| prop | 설명 |
|---|---|
| `value: ProductToken[]` · `onChange` | `ProductToken = { kind: 'model' \| 'family' \| 'custom', ref?, label, model_code? }` |
| `placeholder` · `label` | 숨김 라벨(기본 `제품명 입력`, 버블이 있으면 `제품명 추가 입력`) |
| `legend` | 아래 범례(파란 버블 / 점선 버블) |
| `search(q, signal)` | 검색 바꾸기(기본 kb `/api/kb/v1/products/search`) |
| `maxResults = 5` · `debounceMs = 150` · `placement = 'top' \| 'bottom'` · `compact` · `autoFocus` · `disabled` | |
| `onTokenClick(t)` | 매칭 버블 누르기(예: 제품 시트 열기) |
| `allowCustom = true` | `"q" 그대로 추가`(점선 버블) |
| `qty` · `qtyMax = 9` | 수량 칩 — 매칭 버블 이름 뒤 `×n`(누르면 1~qtyMax 메뉴, 툴팁 `수량 바꾸기`). 새로 넣은 제품은 `qty: 1`. 값은 `ProductToken.qty`(07-image §4.3 `Smart Signage QM55C ×3`) |
| `headText(q)` | 결과 머리 글(기본 `"{q}" 검색 결과 · 방향키로 이동, Enter로 추가` — BE2 는 `(q) => \`"${q}" 검색 결과 · Enter로 추가\``) |
| `rowCta(item, added, active)` | 결과 행 오른쪽(기본: 포커스 행만 `추가 ↵` / 이미 넣은 행 `이미 추가됨`). null 이면 비움 |

키: `↑↓` 이동 · `Enter` 추가(결과가 오기 전이면 오는 대로 첫 행) · `Esc` 패널 닫기 · 빈 입력 `Backspace` 마지막 버블 지우기. 같은 ref(직접 입력은 같은 글)는 두 번 넣지 않는다. 모델 행 · 버블 이름은 표시명(`QM55C`), 제품군은 이름(`실내용 The Wall IWC`).

```tsx
const [items, setItems] = useState<ProductToken[]>([]);
const open = useOpenDetail();
<ProductInput value={items} onChange={setItems} placeholder="제품명 · 모델명을 입력해 추가…" legend
  onTokenClick={(t) => t.model_code && open('product', t.model_code)} />
```
```tsx
// 수량 칩(IMG2 「등장 제품」) — onChange 로 qty 가 바뀐 토큰이 온다
<ProductInput value={items} onChange={setItems} qty qtyMax={9} />
// BE2 머리 글
<ProductInput value={items} onChange={setItems} headText={(q) => `"${q}" 검색 결과 · Enter로 추가`} />
```
함께: `Bubble({ label, custom, onRemove, onClick, qty?, qtyMax?, onQtyChange? })` · `ProductLegend` · `searchProducts(q, { limit, kinds, signal })` · `tokenOf(item)` · `productName(item)` · 타입 `ProductSearchItem`.

## 9. 템플릿 썸네일 (`Thumb.tsx`)

§5.12. 120×68 레이아웃 그림. `code` 가 있으면 export 썸네일(`/api/export/v1/templates/{code}/thumbnail.png`)을 먼저 쓰고, 못 받으면 `kind` 그림(G-UI-1, 셸이 그린 도식).

| prop | 설명 |
|---|---|
| `kind` | `THUMB_KINDS` 중 하나(kpi4 · barline · circles · … 약 75개). 모르면 `table` |
| `n` | 항목 수 1–5 |
| `code` · `src` | export 템플릿 코드 / 직접 주소 |
| `dim` | 고를 수 없는 후보(opacity .45) |
| `title` · `className` | `title` 이 접근 이름(기본 `{code} · {kind} 레이아웃`) |

```tsx
<Thumb code="MS-A" kind="kpi4" n={4} />
<Thumb kind="barline" n={3} dim />
```
`templateThumbUrl(code)` 도 내보낸다.

## 10. 아이콘 (`icons.tsx`)

- `Icon({ name, size = 16, color = 'currentColor', strokeWidth = 2, title, style })` — `name`: search · x · check · info · upload · download · drop · plus · minus · chevronRight/Down/Left/Up · external · link · bolt · lock · edit · trash · refresh · file · image · grip · more · copy · mail · clock · warn · arrowRight/Left/Up · settings · play · stop · folder · user · send · sparkle · undo (`ICON_PATHS`).
- `PathIcon({ d, size, color, strokeWidth })` — 24×24 path 직접.
- `BoltIcon`(딸깍, 채운 번개) · `Grip`(6점 손잡이) · `SlidersIcon` · `FolderIcon({ open })`.
- 기능 아이콘은 셸: `FeatureIcon({ code })` · `FEATURE_ICON` · `SOLUTION_ICON` · `solutionIconPath(id, apiIcon)`.

## 11. 형식 (`format.ts`)

| 함수 | 예 |
|---|---|
| `formatDate(iso, tz = 'Asia/Seoul')` | `2026-10-04T02:10:00Z` → `2026-10-04` |
| `formatDateTime(iso)` | `2026-10-04 11:10` |
| `relativeTime(iso, now)` | `방금` · `12분 전` · `3시간 전` · `어제` · `4일 전` · `9/14` · `2025-12-01` |
| `greetingFor(now)` | `좋은 아침이에요` · `좋은 오후예요` · `좋은 저녁이에요` · 모르면 `안녕하세요` |
| `formatKB(bytes)` | `739867` → `723 KB` |
| `formatBytes(n)` · `formatNumber(n)` | `1.2 MB` · `1,067` |
| `formatMediaSize({width, height, format, bytes}, sep)` | `1340 × 820 · JPG · 368 KB`(용량을 모르면 뺀다) |
| `resolutionLabel(w, h)` | `3840, 2160` → `4K UHD` |
| `shortFileUrl(url)` | `images.samsung.com/kdp/goods/2023/08/29/cc897d99….png` |
| `displayUrl(url)` · `hostOf(url)` | `samsung.com/sec/business/…` · `samsung.com` |
| `josa(word, 받침, 없음)` | `josa('MagicINFO', '이', '가')` → `가` |

## 12. 선택 카드 · Q 상자 (`choice.tsx`)

질의 화면(보드 SB1Q~Q3 · SB3S · SB4U · SB4E — MI · 경쟁사 질의도 같은 모양).

### `ChoiceCard`
h58 r14 패딩 0 18 `<button aria-pressed>`. 선택 = 2px brand 테두리 + `--wm-shadow-choice`.

| prop | 설명 |
|---|---|
| `pressed` · `onClick` | 선택 상태 · 누르기 |
| `kind` | `'radio'`(원형 라디오, 기본) · `'ordered'`(순서 있는 복수 — 고르면 파란 원 순번, 아니면 빈 상자) · `'check'`(체크 상자) · `'none'` |
| `order` | ordered 순번(1부터, 접근 이름에 `{n}번째`) |
| `title` · `hint` · `badge` | 제목(15px — hint 가 있으면 700, 없으면 600 · `weight` 로 바꾸기) · 아래 한 줄 · 제목 옆 배지 |
| `aside` | 오른쪽 역할 라벨(12.5px subtle — `Overview 목적`) |
| `right` | 오른쪽 끝(12.5px muted, `<b>` 는 Manrope 15/800) |
| `icon` | 표시 뒤 40×40 아이콘 상자(SB4E `PPT`) |
| `minHeight` · `weight` · `disabled` · `disabledReason` · `children`(카드 아래 넓은 영역) | |

```tsx
<ChoiceList label="결정할 것">
  {opts.map((o) => <ChoiceCard key={o.id} kind="ordered" pressed={picked.includes(o.id)} order={picked.indexOf(o.id) + 1} title={o.title} aside={o.role} onClick={() => toggle(o.id)} />)}
  <ChoiceCustomInput value={etc} onChange={setEtc} onCommit={addEtc} />
</ChoiceList>
<ChoiceCard kind="radio" pressed={fmt === 'pptx'} icon="PPT" title="PPTX · 스토리보드 양식" hint="섹션 표 그대로 · 편집할 수 있어요" minHeight={84} onClick={() => setFmt('pptx')} />
```

`ChoiceCustomInput({ value, onChange, onCommit, placeholder = '직접 입력', label })` — 점선 `직접 입력` 줄(h52), Enter · 포커스 아웃 때 onCommit. `ChoiceList({ label, children })` — 간격 8 묶음.

### `QBadge`
질의 에이전트 표시 `Q` 상자(흰 바탕 · brand 테두리 1.5 · Manrope 800). `size`: `'md'`(20, 기본) · `'sm'`(18) · `'xs'`(16) · `'lg'`(26) · `'onPrimary'`(주 버튼 안 — 흰 테두리 · 흰 글자).

```tsx
<span className="eyebrow"><QBadge />기획 질의 1 / 3 · 결정할 것</span>
<Button h={48} variant="primary"><QBadge size="onPrimary" />질의 시작</Button>
```

## 13. 키맨 가중치 (`weights.tsx`)

키맨 색(보드 COL 5색) · 아바타 · 점 · 가중치 막대 · − / + 스테퍼 — RQ1 · RQ2 · RQ3 · RQ5 · RQ6 · RQ7B · SB · MI.

| 부품 · 함수 | 설명 |
|---|---|
| `kmClass(colorIndex)` · `kmColors(colorIndex)` | `wm-km wm-km--{i}` 클래스(바탕 · 글자) · `{ bg, fg }` 토큰 |
| `KeymanAvatar({ name, colorIndex, size = 28 })` · `KeymanDot({ colorIndex, size = 8 })` | 이름 첫 글자 원 · 색 점 |
| `WeightBar({ items: WeightItem[], size = 'lg' \| 'md' \| 'sm', onCommit?, showPercent = true, label, min = 5 })` | `WeightItem = { id, name, colorIndex, weight }`. `onCommit` 이 있으면 경계 끌기(1% 단위 · 각 ≥ 5, 놓을 때 onCommit(새 값)) · 경계 손잡이 ←/→. `data-weights` 에 지금 값 |
| `WeightStepper({ value, onStep(±1), label, min = 5, max = 100, disabled })` | `−` · `{n}%` · `+`(h28) — 접근 이름 `{label} 가중치 낮추기/높이기` |
| `equalWeights(n)` · `stepWeights(values, i, ±1)` · `moveWeightBoundary(values, i, delta)` · `distributeWeights(shares, total)` · `WEIGHT_MIN` | 규칙(requirements 서버와 같음): 균등 = floor(100/n) + 앞부터 나머지 · −/+ = 5의 배수로 맞추고 나머지는 비율대로 · 경계 = 이웃 둘만 |

```tsx
const items = keymen.map((k) => ({ id: k.id, name: k.name, colorIndex: k.color_index, weight: k.weight }));
<WeightBar items={items} onCommit={(w) => save(w)} />
<WeightStepper label={k.name} value={k.weight} onStep={(d) => save(stepWeights(items.map((x) => x.weight), i, d))} />
```

## 14. 판단 모드 · 출처 카드 · 근거 패널 (`evidence.tsx`)

보드 MI2A · MIR · MI3S(03-mi §4.4 · §4.11), VPR 범례. 경쟁사 · VP · 제안서(PR7Q 수치 찾기)도 같은 모양.

- `ModeChip({ mode: 'auto' | 'check' | 'ask' | 'pin', dim?, children?, title? })` — h22 칩, 채운 아이콘 10. 글 기본 `MODE_LABELS`(보드 원문 `자동` · `확인 권장` · `선택 필요` · `고정`), 다른 글은 children(`묻기`).
- `SourceCard({ n, kind, kindIcon?: 'web' | 'doc', status: 'ok' | 'warn', statusLabel?, title, meta?, quote?: { before, highlight, after } | string, quoteFromModel?, reason?, flag?, actions?: SourceCardAction[], selected? })` —
  번호 · 종류 · 상태 배지(`원문 일치` brand / `확인 필요` 회색 알약 + 카드 테두리 검정) · 제목 · 메타 · 인용(`<mark>` 하이라이트, 확인 필요면 회색 선) · 사유(정보 아이콘 줄) · 동작 버튼 줄.
  `SourceCardAction = { label, onClick?, href?, icon?: IconName, tone?: 'default' | 'ghost' | 'primary', disabled?, title? }`.
- `EvidencePanel({ title = '출처 · 근거', sub, filters?: { items: { key, label, count }[], value, onChange, label? }, selected?: { label?, text, meta? }, onClose?, closeLabel = '패널 닫기', footer?, width = 420, children })` —
  화면 오른쪽에 붙여 두는 패널(`role="complementary"`, 높이 100%, `--wm-shadow-panel`). 겹창으로 열려면 `SideSheet`.

```tsx
<EvidencePanel sub="시장조사 탭 · 선택한 주장의 출처 2건" onClose={close}
  filters={{ items: [{ key: 'all', label: '전체', count: 2 }, { key: 'public', label: '공개 자료', count: 2 }], value: f, onChange: setF }}
  selected={{ text: claim.text, meta: '출처 2건 · 원문 일치 1 · 확인 필요 1' }}
  footer={<Button h={38} variant="primary">한 번에 확정하기</Button>}>
  <SourceCard n={1} kind="공개 자료 · 시장 보고서" status="ok" title="국내 디지털 사이니지 시장 보고서" meta="[0000]년 발행 · 오늘 확인"
    quote={{ before: '디지털 메뉴보드를 쓰는 매장이 [0]년간 ', highlight: '[00]% 증가' }} actions={[{ label: '원문 열기', icon: 'external', href: url }, { label: '각주로 복사', onClick: copy }]} />
  <SourceCard n={2} kind="공개 자료 · 기사" status="warn" title="…" quote="커피 프랜차이즈의 메뉴보드 디지털 전환 흐름" reason="수치 없이 흐름만 말해요."
    actions={[{ label: '다른 출처 찾기', icon: 'refresh', onClick: find }, { label: '이 출처 빼기', tone: 'ghost', onClick: drop }]} />
</EvidencePanel>
```

## 15. 작업 고르기 (`WorkPicker.tsx`)

`WorkPickerDialog` — 다른 기능의 작업 하나 고르기(검색 · 목록 · 단일 선택 · 확인, 05-vp E2 · E3). workspace `GET /api/workspace/v1/items?feature=&q=&owner=all`.

| prop | 설명 |
|---|---|
| `feature` | 기능 코드(`SB` · `MI` · `VP` …) 하나 또는 배열(합쳐 최근 순) |
| `title` · `confirmLabel = '고르기'` · `onConfirm(item)` · `onClose` | `onConfirm` 이 예외를 던지면 대화상자 아래에 메시지(닫지 않음) |
| `extra` | 목록 아래 칸(노드 또는 `(item) => 노드`) — 복제의 새 고객사 입력 등 |
| `canConfirm(item)` · `disabledReason` | 확인 조건 · 꺼진 이유 |
| `owner = 'all'` · `exclude` · `rowSub(item)` · `placeholder` · `emptyText` · `width = 560` · `limit = 20` · `open = true` | |

키: 검색 칸에서 ↑/↓ 로 고르고 Enter 로 확인 · 행 두 번 누르기 = 확인. 직접 목록만 필요하면 `fetchWorkItems(feature, { q, owner, limit })`.

```tsx
{pick === 'storyboard' && <WorkPickerDialog feature="SB" title="Storyboard 고르기" confirmLabel="이 자료로 시작" onClose={() => setPick(null)}
  onConfirm={async (it) => { const doc = await createVp({ start: 'storyboard', source_refs: [{ kind: 'storyboard', ref_id: it.item_id }] }); nav(`/vp/${doc.id}/materials`); }} />}
```

---

## 셸 API (`@/shell`)

### 기능 등록 — `feature()`
`web/src/features/<기능>/index.tsx` 에서 `export default feature({...})` 만 하면 셸이 모은다(`registry.ts`).

```tsx
export default feature({
  code: 'SP', key: 'spec', name: 'Spec 시트 생성', order: 9,
  routes: [{ index: true, element: <List /> }, { path: 'new', element: <New /> }, { path: ':id/*', element: <Work /> }],
});
```
`FeatureModule = { code, key, name, order, home?, routes, publicRoutes? }`. 기능 10개의 홈 카드 · 사이드바 이름은 셸 카탈로그(`CATALOG` · `SHELL_FEATURES`, §5.1.1 고정 문구)가 정하고, `home` 은 새 기능에만 쓰인다.

- **셸 밖 경로 `publicRoutes`** — 사이드바 · 상단바 없이, 로그인 확인(AUTH_MODE=local) 없이 그리는 최상위 경로(휴대폰 QR 업로드 등). `path` 는 `/` 로 시작하는 절대 경로.
  그 화면에서 401 이 와도 로그인 화면으로 보내지 않는다. 화면은 `useShellPage` 를 불러도 되지만 팝오버 · 상세 시트 · 끌어서 추가는 없다(토스트는 된다).
  ```tsx
  export default feature({ code: 'BE', key: 'birdseye', …, routes: […], publicRoutes: [{ path: '/m/upload/:token', element: <MobileUploadPage /> }] });
  ```
- **기능 격리** — 기능 모듈은 따로 불러온다(`registry.ts`: 동적 import + `Promise.allSettled`, 처음 그리기 전에 끝남). 기능 하나가 import 오류(없는 파일 · 문법 오류 · 빈 모듈)면
  그 기능 경로만 `이 기능을 불러오지 못했어요`(다시 시도 · 홈으로 · 자세한 오류), 화면을 그리다 오류면 기능 경로마다 오류 경계가 `화면을 그리다 문제가 생겼어요` 를 본문에만 보인다.
  사이드바 · 홈 · 다른 기능은 그대로(이름 · 순서는 셸 카탈로그). 불러오지 못한 기능은 `failedFeatures` · `featureLoadFailure(key)`.
  모듈 최상위에서 `features` 를 읽지 않는다(불러오기 전에는 빈 배열).

### 화면 맥락 — `useShellPage(config)`
화면마다 한 번 부른다. 함수 필드는 매번 새로 넘겨도 된다(셸이 최신 것을 부른다).

| 필드 | 타입 | 효과 |
|---|---|---|
| `section` | string | 브레드크럼 두 번째(기능 이름) |
| `title` | string | 브레드크럼 마지막(작업 제목 · `새 작업` · `작업 목록`) |
| `hasTask` | boolean | 진행 중인 작업. 없으면 `section` 이 있을 때 true. **작업 목록 · 빈 화면은 `false` 로** |
| `accepts` | `DragType[]` | 화면에 그 유형의 드롭 영역이 있다 → 팝오버 항목 · 사이드바 항목에 손잡이 · `끌어서 바로 추가` |
| `acceptsWork` | `FeatureCode[]` | `accepts` 에 `work_item` 이 있을 때 끌 수 있는 사이드바 기능(없으면 전부) |
| `added` | `Ref[]` | 이미 들어간 참조 → 팝오버 `✓ 추가됨`(끌기 · 선택 불가) |
| `onAdd(type, refs)` | `→ { added: Ref[] }` | 팝오버 `현재 작업에 추가` · 시트 `현재 작업에 추가` / `작업에 추가`. 없으면 버튼이 꺼지고 `이 화면에서는 추가할 수 없습니다` |
| `addable` | `DragType[]` | `onAdd` 가 받는 유형(없으면 product · solution · image · case) |
| `onAttach(images)` | | 이미지 `대화에 첨부` · `{N}장 대화에 첨부`. 이미지마다 `ref` · 출처 메타(`source_page` · `original_url` · `usage_note` …)가 온다 |
| `stepper` | `StepperConfig` | 상단바 아래 스텝바 |
| `sidebarGroup` | 기능 key | 펼쳐 둘 사이드바 그룹(없으면 현재 라우트) |
| `taskContext` | `{ verticalId?, verticalName?, products?: {ref, label}[] }` | 유관 사례 기본 업종(`vertical_from=task`) · `제품:` 메뉴 |

규칙(§5.2.3):
- 작업 없음 → 팝오버는 탐색만(추가 버튼 비활성 + 이유, 푸터 안내). 시트 추가 버튼 `title="진행 중인 작업이 없습니다"`.
- 작업 있음 + `onAdd` → `+ 추가` 로 고르고 `현재 작업에 추가`(키보드만으로도 된다, X-04). 실패하면 `추가하지 못했어요` + 다시 시도.
- 작업 있음 + `accepts` 에 유형 → 끌기. 놓아 성공하면 그 항목이 `✓ 추가됨`.
- 셸이 표시하는 `✓ 추가됨` 은 `added` 와 이번 세션에 추가한 것(작업 경로가 바뀌거나 `added` 가 바뀌면 `added` 가 원천).

```tsx
useShellPage({
  section: 'B2B 제안서 생성', title: draft.title, accepts: ['product', 'solution', 'image', 'case', 'work_item'], acceptsWork: ['MI', 'VP'],
  added: draft.refs, addable: ['product', 'solution', 'case'],
  onAdd: async (type, refs) => ({ added: await api.addRefs(draft.id, type, refs) }),
  onAttach: (images) => chat.attach(images),
  taskContext: { verticalId: 'kr_retail_fnb', verticalName: '유통/요식', products: [{ ref: 'kb:family:fam_G000182628', label: 'QMC' }] },
  stepper: {
    steps: ['고객 · 프로젝트', '제안서 유형', '시트 구성', '섹션 작성', '디자인 템플릿', 'PPTX 생성'], current: 4,
    oneClick: { onRun: ({ markInferred, collectReview }) => startJob({ markInferred, collectReview }), running: job.running },
  },
});
```

참조 문자열(`Ref`): `kb:model:mdl_…` · `kb:family:fam_…` · `kb:solution:<카탈로그 id>`(예 `magicinfo`) · `kb:image:img_…` · `kb:case:dep_…` · `ws:item:<id>` · `img:image:<id>` · `custom:<글>`. 만들기 · 풀기: `ref.model(id)` … · `parseRef(r)`.

### 스텝바 — `StepperConfig`
| 필드 | 설명 |
|---|---|
| `steps` · `current`(1부터) | 단계 이름 · 현재 |
| `complete` | 모두 끝(전부 체크, 딸깍 없음, 가운데 정렬) |
| `autoFrom` · `auto` | 딸깍이 채운 단계(검은 번개 원) |
| `onStep(k)` | 있으면 단계를 누를 수 있다(보드는 불가 — Q-UI-6) |
| `oneClick` | `{ label?, onRun({ markInferred, collectReview }), disabled?, running? }` — `딸깍, 완성하기` 에서 한 번 |
| `oneClickOpen` · `planConfirmed` · `planRows: {label, note}[]` · `planSummary` | 딸깍 팝오버 내용(기본: 앞 단계 = 확정, 현재부터 = 추론) |
| `right` | 오른쪽에 둘 요소 |

단계 6개 이상이면 이름 12.5px · 선 28, 4–5개 40, 3개 이하 56.

### WorkListPage
기능의 `작업 목록` 기본형(보드 RQ0 · CA0 · MI0 · SP0). 브레드크럼 `… / 작업 목록`, `hasTask: false` 를 스스로 건다.

```tsx
routes: [{ index: true, element: <WorkListPage feature="RQ" title="고객 요구사항" newLabel="새 요구사항" /> }, …]
```
props: `feature` · `title` · `desc` · `newLabel = '새로 만들기'` · `newTo`(기본 `/<key>/new`) · `crumb = '작업 목록'` · `statusMap`(상태 값 → `{ label, tone, icon?, running? }`) · `extraColumns` · `banner` · `footer` · `emptyText`.

### 팝오버 · 상세 시트 · URL
상단바 팝오버 4종(제품 탐색 · 솔루션 탐색 · 이미지 검색 · 유관 사례 검색)과 상세 시트 2종(제품 · 솔루션, 탭 3개씩)은 셸 것이다. 상태는 URL 에 있어 새로고침 · 링크 공유 · 뒤로 가기가 된다.

| 쿼리 | 값 |
|---|---|
| `pop` | `product` · `solution` · `image` · `case` |
| `q` | 팝오버 검색어 |
| `node` | 제품 트리 노드(`top_…` · `cat_…` · `fam_…`) |
| `detail` | `product:<모델코드>` · `solution:<id>` |
| `tab` | 제품 `spec` · `images` · `cases` / 솔루션 `overview` · `images` · `cases` |
| `img` | 시트 이미지 탭에서 고른 이미지 id |

```tsx
const openDetail = useOpenDetail();   openDetail('product', 'LH55QMCEBGCXKR', 'images');
const openPop = useOpenPopover();     openPop('case', '프랜차이즈 메뉴보드');
<Link to={{ search: detailHref('solution', 'magicinfo') }}>MagicINFO 상세</Link>
const { pop, q, detail, tab, update } = useShellUrl();  update({ pop: null });
```

### kb 데이터 훅 · 도우미
타입은 `contracts/kb.json` 에서 생성한 `@/api/gen/kb` 에 셸 이름을 붙인 것(`kbTypes.ts`: `KbModelDetail` · `KbImageMeta` · `KbCaseCard` …). 갱신: `cd web && node scripts/gen-api.mjs kb`.

- 훅: `useKbMeta` · `useCategories(parentId)` · `useFamilies(categoryId)` · `useModels({ family_id | category_id | q })` · `useModel(code)` · `useModelImages(code)` · `useModelCases(code, match?)` · `useSolutions({ q, industry })` · `useSolution(id)` · `useSolutionImages(id)` · `useSolutionCases(id)` · `useImageSearch({ q, source, verified_only })` · `useImageMeta(id)` · `useCaseSearch({ q, vertical_id, vertical_from, target, period, infer_vertical })` · 쪽 단위(`더 보기`) `useImageSearchPages` · `useCaseSearchPages` · `useVerticals()` · `useMyImages(q)`(image 서비스, 없으면 빈 목록).
- 직접 호출: `kb.model(code)` … · `kbGet(path, params)` · `getJson(url)`(오류는 `ApiError`).
- 도우미: `modelName(m)`(표시명, 없으면 모델코드 — G-PRD-1) · `seriesCode('QMC Series')` → `QMC` · `imageSrc(im, 'thumb' | 'stored')` · `imageAlt(im, fallback)`(`img` 같은 빈 alt 건너뜀) · `imageKindLabel(kind)` · `usageNotePopover(rights)` · `usageNoteSheet(rights)`(kb `usage_note` 가 있으면 그것이 먼저).
- 사례 검색 `target` 은 `kb:` 없이 `family:fam_…` · `model:mdl_…` · `category:cat_…` · `solution:<id>`. `region` 은 kb 가 아직 400(G-CASE-4).

### workspace 훅
`useMe()`(인사말 · 사용자 카드 — `role` · `username` · `has_password` 포함) · `useItemCounts()` · `useFeatureItems(code, limit)` · `useRecentItems(limit)` · `useAssetUsage(refs)` + `usageText(data, ref)`(`Winmate 제안서 N건`)
· `useNotificationCounts()`(읽지 않은 작업물 알림 — 전체 · 항목별) · `useNotifications(limit)` · `markNotificationsRead({ ids? | item_id? })` · `useUsers()`.

### 작업물 알림 [제안]
기능 서비스가 workspace `POST /v1/notifications {item_id, title, route?, type?, message?, ref?}`(internal)로 보내면 그 항목 주인에게 간다.
셸은 사이드바 그 항목에 읽지 않은 수(파란 알약) · 그룹 이름 옆 점, 사용자 메뉴(설정 버튼)에 알림 목록(최근 8 · `모두 읽음`)을 보인다. 그 작업물 화면을 열면(경로에 항목 id) 읽음으로 바뀐다.
검토(`/v1/reviews`) 요청 · 결정 · 다시 요청도 같은 알림을 만든다(`review_requested` · `review_decided` · `review_resubmitted`) — 마감일(`data.due_date`)이 있으면 알림 줄에 `D-n` · `D-day` · `마감 지남`.

### 로그인 · 401 (AUTH_MODE=local)
- `/login?next=` — 셸 밖 로그인 화면(게이트웨이 `POST /api/_auth/login`). 로그인하면 쿼리 캐시를 비우고 `next`(같은 사이트 경로만)로 돌아간다.
- 셸 경로는 `AuthGate`(`shell/auth.tsx`)가 감싼다: `GET /api/_auth/me` 가 401 이면 `/login?next=<지금 화면>`. API 가 401 을 주면(아래 세 곳에서 알림) 같은 곳으로 보낸다.
  - `@/api/client` 의 openapi 클라이언트(미들웨어) · `uploadFile` · 전역 감시(`installAuthGuard()`, main.tsx 가 설치 — 기능 화면의 `fetch('/api/…')` 401 과
    `new EventSource('/api/…')` 가 아주 끊긴 경우(`/api/_auth/me` 로 확인)도 잡힌다)
  - `@/api/jobs` 의 잡 fetch · SSE 가 끊기면 `/api/_auth/me` 로 확인(`probeAuth()`)
  - 직접 쓰려면 `onUnauthorized(fn)` · `reportUnauthorized(res, url)`. 로그인 API(`/api/_auth/…`)의 401 은 알리지 않는다.
- 사용자 메뉴(사이드바 설정 버튼): 로그인한 사용자(아이디 · 역할) · `사용자 관리`(관리자 · AUTH_MODE=none) · `비밀번호 바꾸기` · `로그아웃`(local 만).
- `/admin/users` — 사용자 관리(만들기 · 이름 · 소속 · 역할 · 비밀번호 재설정 · 사용 중지). AUTH_MODE=none 이면 누구나(개발).
- AUTH_MODE=none(개발)이면 `/api/_auth/me` 가 늘 개발 사용자라 로그인 화면이 나오지 않는다(`/login` 은 바로 `next` 로).

### 카탈로그
`CATALOG`(홈 카드 · §5.1.1 문구) · `shellFeatures()`(코드 · key · 이름 · 순서 · `listRoute` · `newRoute`, 처음 쓸 때 계산 — 예전 이름 `SHELL_FEATURES` 도 됨) · `featureName(code)` · `shellFeatureByKey` · `shellFeatureByCode` · `features` · `featureByKey` · `featureByCode`(등록된 모듈).

## 개발 화면

개발 · 시험용 경로(지연 로딩). 운영 빌드에서 빼려면 `VITE_WM_DEVTOOLS=0 npx vite build`.

- `/_dev/kit` — 부품 견본(제품 입력창 · 버튼 · 칩 · 배지 · 썸네일 · 목록 뼈대 · 사례 카드 · 확인창 · 토스트 + 분할 버튼 · 큰 스위치 · 선택 카드 · Q 상자 · 키맨 가중치 · 판단 모드 · 출처 카드 · 근거 패널 · 메아리 말풍선 · 수량 칩 · 오른쪽 시트 · 작업 고르기).
- `/_dev/shell` — 작업 맥락 흉내. 쿼리:
  `task=1` · `accepts=product,solution,image,case,work_item` · `work=MI,SP` · `added=<ref,…>` · `fail=1`(onAdd · onDrop 실패) · `noattach=1` · `group=<기능 key>` · `steps=a,b,c` 또는 `steps=proposal` · `current=2` · `complete=1` · `autoFrom=4` · `oneClick=1` · `open=1` · `vertical=kr_retail_fnb:유통/요식`
  + 셸 쿼리(`pop` · `q` · `node` · `detail` · `tab` · `img`). onAdd · onAttach · onDrop · undo · oneClick 호출이 화면 아래 로그와 `window.__wmShellLog` 에 남는다.

예: `/_dev/shell?task=1&accepts=product&pop=product&node=fam_G000182628` → QMC 행을 아래 드롭 영역에 끌어 본다.

## 시험

```bash
cd web && npx tsc -b --noEmit && npx vite build
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers npx playwright test e2e/shell
```
- `web/e2e/shell/*.spec.ts` — §8 수용 기준(L · N · H · T · P · S · I · C · D · PD · SD · PI · ST · X). kb 는 route 흉내(`fixtures/mock.ts`, KB v1 값), `live.spec.ts` 는 실제 workspace · kb(kb 가 꺼져 있으면 건너뜀).
  `auth.spec.ts`(로그인 · 401 · 로그아웃 · 셸 밖 경로 — `/api/_auth/*` route 흉내) · `isolation.spec.ts`(기능 하나 import 오류 · 그리기 오류, 개발 서버에서만) · `kit-more.spec.ts`(더한 부품) · `notify.spec.ts`(알림 배지 · 사용자 메뉴 · 사용자 관리).
- 셸 e2e(개발 서버): `cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=shell WM_E2E_DEV=1 WM_E2E_PORT=5197 npx playwright test e2e/shell --workers=1`
- 화면 캡처: `web/e2e/shell/__screens__/`(흉내 데이터 · `live-*` 는 실제 kb).
- dist 를 다른 세션이 다시 빌드하는 중이면 `WM_E2E_PREVIEW=1` 로 따로 빌드해 돈다. 설치된 Chromium 판이 다르면 설정이 있는 판을 찾아 쓴다(`PW_CHROMIUM_PATH`).
