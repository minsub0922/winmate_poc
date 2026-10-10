/**
 * API 흉내 위의 화면 테스트(§9.1) — 실제 서비스로 만들기 어려운 상태를 고정값으로:
 * AC-MI-04 · 09 · 10 · 11(MI1Q) · 20 · 21 · 22(MI3G · 미리 보기) · 42 · 89(MI3S) · 75(MI0 배너 · 행 메뉴).
 */
import { expect, test } from '@playwright/test';
import { AID, ASK, analysis, designView, mockJobs, mockMi, result, runSnapshot, sse } from './mock';
import { shot } from './helpers';

test('MI1Q — 업종 두 갈래면 묻고, 고른 업종으로 분석을 시작한다 (AC-MI-04 · 09 · 10 · 11)', async ({ page }) => {
  let answered: any = null;
  const memos: string[] = [];
  let polls = 0;
  await mockMi(page, {
    [`GET /v1/analyses/${AID}`]: () => analysis(answered ? { status: 'queued', current_job_id: 'job_run' } : {}),
    [`PATCH /v1/analyses/${AID}`]: () => analysis(),
    [`GET /v1/analyses/${AID}/design`]: () => designView(),
    [`POST /v1/analyses/${AID}/design/memo`]: (_r: unknown, _u: unknown, _m: unknown, body: any) => { memos.push(body.text); return { job_id: 'job_ask', status: 'queued' }; },
    [`GET /v1/analyses/${AID}/progress`]: { job_id: 'job_run', status: 'queued', pct: 0, eta_s: 180, stage: null, stages: [], areas: [], sources: {}, recent_sources: [], previewable: [],
      summary_chip: '분석 시작 · 4개 영역 · 경쟁사 A · B · C · 비교 기준 4개', card_title: '시장 · 경쟁사 분석 중', card_sub: '4개 영역 · 경쟁사 3', error: null, memos: [] },
  });
  await mockJobs(page, {
    job_ask: {
      snapshot: () => (answered ? { id: 'job_ask', service: 'mi', kind: 'mi.design', status: 'succeeded', progress: 100, message: '완료', result: { analysis_id: AID, next_job_id: 'job_run' } }
        : { id: 'job_ask', service: 'mi', kind: 'mi.design', status: 'awaiting_input', progress: 60, message: '선택 필요', input_request: ASK }),
      events: () => {
        polls += 1;
        if (answered) return sse([{ type: 'result', data: { analysis_id: AID, next_job_id: 'job_run' } }, { type: 'done', data: { status: 'succeeded' } }]);
        return sse(polls === 1 ? [{ type: 'awaiting_input', data: ASK }] : [], 300);
      },
      onInput: (b) => { answered = b; },
    },
    job_run: { snapshot: () => ({ id: 'job_run', service: 'mi', kind: 'mi.analyze', status: 'queued', progress: 0, message: '대기 중' }), events: () => sse([]) },
  });

  // 설계 화면으로 들어와도 묻는 중이면 MI1Q 로(AC-MI-04)
  await page.goto(`/mi/${AID}/design`);
  await expect(page).toHaveURL(new RegExp(`/mi/${AID}/design/industry$`));
  await expect(page.getByText(ASK.agent_text)).toBeVisible();
  const card = page.getByTestId('mi1q-card');
  await expect(card.getByText('어느 업종 관점으로 분석할까요?')).toBeVisible();
  await expect(card.getByText('1 · 2위 차이 0.03 · 기준 0.10 미만')).toBeVisible();
  const opts = page.getByRole('radiogroup', { name: '업종 선택지' }).getByRole('radio');
  await expect(opts).toHaveCount(3);
  await expect(opts.nth(0)).toHaveAttribute('aria-checked', 'true');
  await expect(opts.nth(0)).toContainText('추천');
  await expect(opts.nth(2)).toContainText('0.57');
  await expect(opts.nth(2)).toContainText('MI-HT-A · B + MI-FB-C');
  await expect(page.getByText('답이 없으면 추천(호텔 · 리조트)으로 진행하고, 결과 화면의 업종 칩에서 언제든 바꿀 수 있어요.')).toBeVisible();
  await expect(page.getByTestId('mi-dock-title')).toHaveText('업종 확인 · 선택 필요 1 · 나머지 6개는 자동으로 정했어요');
  const go = page.getByTestId('mi1q-go');
  await expect(go).toHaveText('호텔 · 리조트로 분석 시작');
  await shot(page, 'mi1q-ask');

  // 섞어서 보기를 고르면 큰 버튼 문구가 따라 바뀐다
  await opts.nth(2).click();
  await expect(go).toHaveText('섞어서 보기로 분석 시작');
  await opts.nth(1).click();
  await expect(go).toHaveText('외식 · 카페로 분석 시작');

  // 판단에 도움이 될 말 → 같은 잡 메모 · 화면은 MI1Q 에 남는다(AC-MI-11)
  await page.getByLabel('판단에 도움이 될 말').fill('결재는 호텔 F&B 팀장');
  await page.getByRole('button', { name: '보내기' }).click();
  await expect.poll(() => memos).toEqual(['결재는 호텔 F&B 팀장']);
  await expect(page).toHaveURL(new RegExp(`/design/industry$`));
  await expect(page.getByTestId('mi-user').last()).toHaveText('결재는 호텔 F&B 팀장');

  // 섞어서 보기로 시작 → jobs input {answer:{segment:"MIX", start_analysis:true}} → MI3G(AC-MI-09 · 10)
  await opts.nth(2).click();
  await go.click();
  await expect.poll(() => answered).not.toBeNull();
  expect(answered.answer.segment).toBe('MIX');
  expect(answered.answer.start_analysis).toBe(true);
  await expect(page).toHaveURL(new RegExp(`/mi/${AID}/run$`), { timeout: 15_000 });
});

test('MI3G — 진행률 · 남은 시간 · 먼저 끝난 영역 미리 보기 (AC-MI-20 · 21 · 22)', async ({ page }) => {
  const snap = runSnapshot();
  await mockMi(page, {
    [`GET /v1/analyses/${AID}`]: analysis({ status: 'running', current_job_id: 'job_run', segment: { code: 'FB', mode: 'auto', confidence: 0.94, candidates: [], clues: [] }, title: 'A 커피 시장 · 경쟁사 분석' }),
    [`PATCH /v1/analyses/${AID}`]: analysis(),
    [`GET /v1/analyses/${AID}/progress`]: { job_id: 'job_run', status: 'running', pct: 40, eta_s: 120, stage: 'organize', ...snap,
      summary_chip: '분석 시작 · 4개 영역 · 경쟁사 A · B · C · 비교 기준 5개', card_title: '시장 · 경쟁사 분석 중', card_sub: '4개 영역 · 경쟁사 3', error: null, memos: [] },
    [`GET /v1/analyses/${AID}/result`]: (_r: unknown, url: URL) => result(['1', 'true'].includes(url.searchParams.get('preview') ?? '')),
  });
  await mockJobs(page, {
    job_run: {
      snapshot: () => ({ id: 'job_run', service: 'mi', kind: 'mi.analyze', status: 'running', progress: 40, message: '정리 중' }),
      events: () => sse([{ type: 'step', data: snap }, { type: 'progress', data: { progress: 58, eta_s: 90, stage: 'organize' } }]),
    },
  });
  await page.goto(`/mi/${AID}/run`);
  await expect(page.getByTestId('mi3g-pct')).toHaveText('58% · 약 1분 30초 남음');
  await expect(page.getByRole('progressbar', { name: '분석 진행률' })).toHaveAttribute('aria-valuenow', '58');
  await expect(page.getByTestId('mi-user')).toHaveText('분석 시작 · 4개 영역 · 경쟁사 A · B · C · 비교 기준 5개');
  await expect(page.locator('[data-stage-status]')).toHaveText([/1 검색출처 31곳 확인 · 완료/, /2 정리영역 2 \/ 4 정리됨/, /3 작성결과 · 비교표 · 삼성 강점/]);
  await expect(page.locator('.mi-area')).toHaveText([/시장조사.*정리 완료/, /고객사 · 비즈니스.*정리 완료/, /사용자.*정리 중/, /경쟁사 → 삼성 강점.*대기/]);
  await expect(page.getByTestId('mi3g-src-total')).toHaveText('31');
  await expect(page.getByText('사용 18 · 확인 중 9')).toBeVisible();
  await expect(page.getByTestId('mi3g-preview')).toContainText('먼저 끝난 영역부터 볼 수 있어요 · 시장조사 · 고객사 · 비즈니스');
  await expect(page.getByRole('button', { name: '중지' })).toHaveAttribute('title', '중지하고 설정으로 돌아가요. 정리된 영역은 남겨 둡니다.');
  await shot(page, 'mi3g-progress');

  await page.getByRole('link', { name: '정리된 내용 미리 보기' }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/${AID}/result\\?preview=1`));
  await expect(page.getByTestId('mi-dock-title')).toHaveText('분석 결과 · 3 / 3 · 정리 중');
  await expect(page.getByTestId('mi3-send')).toBeDisabled();
  await expect(page.getByRole('tab', { name: /사용자/ })).toBeDisabled();
  await expect(page.getByRole('tab', { name: /사용자/ })).toContainText('정리 중');
  await expect(page.getByRole('tab', { name: '시장조사' })).toBeEnabled();
  await shot(page, 'mi3-preview');
});

test('MI3S — 탭 배지 · 확인 필요 합계 · 출처 카드 동작 (AC-MI-42 · 89)', async ({ page }) => {
  const items = [
    { id: 'clm_m1', area: 'market', text: '국내 F&B 매장의 디지털 메뉴보드 도입이 최근 [00]년간 [00]% 늘었습니다', status: 'needs_check', label: '확인 필요 1',
      citations: [{ n: 1, source_id: 'src_1', status: 'matched' }, { n: 2, source_id: 'src_2', status: 'unverifiable' }], inferred: false, block_path: 'trends.0' },
    { id: 'clm_m2', area: 'market', text: '프로모션 주기가 짧아져 메뉴 콘텐츠를 바꾸는 횟수가 늘고 있습니다', status: 'matched', label: '원문 일치',
      citations: [{ n: 3, source_id: 'src_3', status: 'matched' }], inferred: false, block_path: 'trends.1' },
  ];
  const card = (n: number, kind: string, status: string, actions: string[], extra: Record<string, unknown> = {}) => ({
    n, source_id: `src_${n}`, kind, kind_label: kind === 'websearch_summary' ? '웹 검색 요약' : '공개 자료 · 시장 보고서', status,
    status_label: status === 'matched' ? '원문 일치' : '확인 필요', title: kind === 'websearch_summary' ? '웹 검색 요약 · F&B 메뉴보드' : '[조사 기관] 국내 디지털 사이니지 시장 보고서',
    meta: kind === 'websearch_summary' ? '원문 URL 없음 · 10월 6일 검색' : '2026년 3월 발행 · p.12 · 오늘 확인', quote: '디지털 메뉴보드를 쓰는 매장이 3년간 42% 증가',
    quote_before: '디지털 메뉴보드를 쓰는 매장이 3년간 ', quote_highlight: status === 'matched' ? '42% 증가' : '', quote_after: '', quote_style: kind === 'websearch_summary' ? 'summary' : 'normal',
    reason: status === 'matched' ? '' : '검색 요약에서 나온 내용이라 원문과 대조하지 못했어요.', reason_code: null, actions, url: kind === 'web' ? 'https://example.org/report' : null,
    file_id: null, page: null, footnote: '각주', flag: '', has_snapshot: false, ...extra,
  });
  await mockMi(page, {
    [`GET /v1/analyses/${AID}`]: analysis({ status: 'done', version: 1, title: 'A 커피 시장 · 경쟁사 분석' }),
    [`PATCH /v1/analyses/${AID}`]: analysis({ status: 'done', version: 1 }),
    [`GET /v1/analyses/${AID}/result`]: result(false),
    [`GET /v1/analyses/${AID}/claims`]: { items, tab_sources: { total: 7, public: 5, kb_case: 2, kb_official: 0, internal: 0, needs_check: 3 },
      badges: { market: 3, customer: 1, user: 0, competitor: 2 }, needs_check_total: 6, summary_text: '이 탭 출처 7건 · 공개 자료 5 · 사내 사례 DB 2' },
    [`GET /v1/analyses/${AID}/claims/clm_m1`]: { claim: items[0], tab: 'market', tab_label: '시장조사',
      cards: [card(1, 'web', 'matched', ['원문 열기', '각주로 복사']), card(2, 'websearch_summary', 'unverifiable', ['각주로 복사', 'URL 붙여 확인', '다른 출처 찾기', '값 직접 확정', '이 출처 빼기'])],
      counts: { total: 2, matched: 1, needs_check: 1 }, conflict: null, fix_id: 'fix_1' },
  });
  await page.goto(`/mi/${AID}/result?tab=market&panel=sources&claim=clm_m1`);
  const tabs = page.getByRole('tablist', { name: '분석 영역' }).getByRole('tab');
  await expect(tabs).toHaveText(['시장조사3', '고객사 · 비즈니스1', '사용자', '경쟁사 → 삼성 강점2']);
  await expect(tabs.nth(0).locator('.mi-tab__badge')).toHaveAttribute('title', '확인 필요 3건');
  await expect(tabs.nth(2).locator('.mi-tab__badge')).toHaveCount(0);
  await expect(page.getByTestId('mi-dock-title')).toHaveText('근거 확인 · 확인 필요 6건 남음');
  await expect(page.getByTestId('mi3s-tab-summary')).toHaveText('이 탭 출처 7건 · 공개 자료 5 · 사내 사례 DB 2');
  const panel = page.getByRole('complementary', { name: '출처 · 근거' });
  await expect(panel.getByRole('tab')).toHaveText(['전체7', '공개 자료5', '사내 사례 DB2', '확인 필요3']);
  await expect(panel.getByText('시장조사 탭 · 선택한 주장의 출처 2건')).toBeVisible();
  await expect(panel.getByTestId('mi3s-selected')).toContainText('출처 2건 · 원문 일치 1 · 확인 필요 1');
  const cards = panel.getByTestId('mi3s-card');
  await expect(cards.nth(0).getByRole('button', { name: '원문 열기' })).toBeVisible();
  await expect(cards.nth(0).locator('mark')).toHaveText('42% 증가');
  await expect(cards.nth(1).getByRole('button', { name: '원문 열기' })).toHaveCount(0);
  await expect(cards.nth(1).getByRole('button', { name: 'URL 붙여 확인' })).toBeVisible();
  await expect(cards.nth(1)).toContainText('검색 요약에서 나온 내용이라 원문과 대조하지 못했어요.');
  await shot(page, 'mi3s-panel-board');

  // `확인 필요만 보기` → 원문 일치 주장은 숨긴다
  await page.getByRole('button', { name: '확인 필요만 보기' }).click();
  await expect(page.locator('.mi-crow')).toHaveCount(1);
  // `URL 붙여 확인` → 출처 추가 폼
  await cards.nth(1).getByRole('button', { name: 'URL 붙여 확인' }).click();
  await expect(panel.getByTestId('mi3s-addsrc')).toBeVisible();
  // `값 직접 확정` → MI3V(그 항목)
  await cards.nth(1).getByRole('button', { name: '값 직접 확정' }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/${AID}/verify\\?fix=fix_1`));
});

test('MI0 — 머리 집계 · 상태 필터 · 업데이트 배너 · 행 동작과 메뉴 (AC-MI-75)', async ({ page }) => {
  const row = (id: string, title: string, status: string, tone: string, label: string, note: string, action: [string, string], extra: Record<string, unknown> = {}) => ({
    id, title, version: status === 'draft' ? 0 : 1, owner_name: '최민섭', time_label: '2시간 전 수정', sub: '최민섭 · 2시간 전 수정', segment: 'FB', segment_label: '외식 · 카페',
    scope_label: status === 'draft' ? '범위 선택 전' : '시장 · 고객 · 사용자 · 경쟁', scope_selected: status !== 'draft', status, status_label: label, status_tone: tone, note,
    proposal_title: null, action: { label: action[0], route: action[1], kind: 'open' }, menu: [], changes_head: null, route: `/mi/${id}/result`, updated_at: '2026-10-06T00:00:00Z',
    current_job_id: null, fix_open: 0, has_competitors: true, ...extra,
  });
  const upd = (id: string, title: string) => row(id, title, 'upd', 'upd', '업데이트 필요', '경쟁사 신제품 감지 1건', ['다시 분석', `/mi/${id}/run`], {
    action: { label: '다시 분석', route: `/mi/${id}/run`, kind: 'rerun' },
    changes_head: { title: '바뀐 자료 2건', summary: '경쟁사 A 신제품 발표 · 시장 리포트 개정 [기관, 연도]' },
    menu: [
      { key: 'changed_only', label: '바뀐 부분만 다시 분석', hint: '시장 · 경쟁 · 약 1분', route: `/mi/${id}/run`, highlight: true },
      { key: 'full', label: '전체 다시 분석', hint: 'v2로 저장 · v1 보관', route: `/mi/${id}/run`, highlight: false },
      { key: 'open_last', label: '지난 결과 열기', hint: 'v1 · 9월 1일', route: `/mi/${id}/result?version=1`, highlight: false },
      { key: 'send', label: '제안서 MI 섹션으로 보내기', hint: 'B 병원 제안', route: `/mi/${id}/export`, highlight: false },
      { key: 'duplicate', label: '복제해서 새 분석', hint: '범위 그대로', route: null, highlight: false }],
  });
  const ids = ['mi_01M4E2EMOCK00000000000001', 'mi_01M4E2EMOCK00000000000002', 'mi_01M4E2EMOCK00000000000003', 'mi_01M4E2EMOCK00000000000004', 'mi_01M4E2EMOCK00000000000005'];
  const items = [
    row(ids[0], 'A 커피 프랜차이즈 시장·경쟁사 분석', 'done', 'done', '완료', '출처 18곳 · 확정 필요 수치 3', ['수치 확정', `/mi/${ids[0]}/verify`], { fix_open: 3 }),
    upd(ids[1], 'B 병원 환자 동선 분석'),
    row(ids[2], 'C 물류센터 경쟁사 벤치마크', 'running', 'run', '진행 중', '정리 중 · 출처 24곳 확인', ['진행 보기', `/mi/${ids[2]}/run`]),
    row(ids[3], 'D 대학 강의동 협업 공간 시장 분석', 'draft', 'draft', '작성 중', '고객 요구사항까지 입력', ['이어서', `/mi/${ids[3]}/scope`]),
    upd(ids[4], 'B 병원 경쟁사 키오스크 비교'),
  ];
  await mockMi(page, {
    'GET /v1/analyses': { items, next_cursor: null, counts: { all: 5, run: 1, done: 1, upd: 2, draft: 1 }, fix_open_works: 1,
      upd_changes: { [ids[1]]: { title: '바뀐 자료 2건', summary: '경쟁사 A 신제품 발표 · 시장 리포트 개정' }, [ids[4]]: { title: '바뀐 자료 1건', summary: '경쟁사 B 신제품 발표' } },
      banner: { n: 2, title: '2건은 다시 분석을 권해요.', text: '분석한 지 30일이 지났고, 그사이 경쟁사 신제품 발표와 시장 리포트 개정이 확인됐어요.', kinds: [], target_ids: [ids[1], ids[4]] },
      header: '분석 5건 · 업데이트 필요 2건 · 확정 필요 수치가 남은 작업 1건' },
  });
  await page.goto('/mi/legacy');
  await expect(page.getByTestId('mi0-header')).toHaveText('분석 5건 · 업데이트 필요 2건 · 확정 필요 수치가 남은 작업 1건');
  await expect(page.getByRole('tablist', { name: '상태 필터' }).getByRole('tab')).toHaveText(['전체5', '진행 중1', '완료1', '업데이트 필요2', '작성 중1']);
  await expect(page.getByTestId('mi0-banner')).toContainText('2건은 다시 분석을 권해요. 분석한 지 30일이 지났고, 그사이 경쟁사 신제품 발표와 시장 리포트 개정이 확인됐어요.');
  await expect(page.getByRole('button', { name: '2건 다시 분석' })).toBeVisible();
  await expect(page.locator('.mi-trow:not(.mi-trow--head) .mi-act')).toHaveText(['수치 확정', '다시 분석', '진행 보기', '이어서', '다시 분석']);
  await page.getByRole('button', { name: 'B 병원 환자 동선 분석 메뉴' }).click();
  const menu = page.getByRole('menu', { name: 'B 병원 환자 동선 분석 작업 메뉴' });
  await expect(menu).toBeVisible();
  await expect(menu).toContainText('바뀐 자료 2건');
  await expect(menu.getByRole('menuitem')).toHaveText([/바뀐 부분만 다시 분석시장 · 경쟁 · 약 1분/, /전체 다시 분석v2로 저장 · v1 보관/, /지난 결과 열기v1 · 9월 1일/,
    /제안서 MI 섹션으로 보내기B 병원 제안/, /복제해서 새 분석범위 그대로/]);
  await shot(page, 'mi0-list-board');
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: '바뀐 자료 보기' }).click();
  await expect(page.getByRole('dialog', { name: '바뀐 자료' })).toContainText('B 병원 환자 동선 분석 · 바뀐 자료 2건');
});

test('MI1 — 입력 없으면 비활성, 고객사만 넣어도 활성 · 800ms 뒤 draft 생성 (AC-MI-86)', async ({ page }) => {
  let created: any = null;
  let createdAt = 0;
  let typedAt = 0;
  await mockMi(page, {
    'POST /v1/analyses': (_r: unknown, _u: unknown, _m: unknown, body: any) => { created = body; createdAt = Date.now(); return analysis({ status: 'draft', customer_name: body.customer_name, title: '' }); },
    [`GET /v1/analyses/${AID}`]: () => analysis({ status: 'draft', customer_name: created?.customer_name ?? '', title: '', requirements_text: '' }),
    [`PATCH /v1/analyses/${AID}`]: () => analysis({ status: 'draft' }),
  });
  await page.route((u) => u.pathname === '/api/workspace/v1/items' && u.searchParams.get('feature') === 'SB', (r) => r.fulfill({ json: { items: [], next_cursor: null } }));
  await page.goto('/mi/legacy/new');
  const next = page.getByTestId('mi1-next');
  await expect(next).toBeDisabled();
  typedAt = Date.now();
  await page.getByLabel('고객사').fill('A 커피');
  await expect(next).toBeEnabled();
  await expect.poll(() => created?.customer_name, { timeout: 5_000 }).toBe('A 커피');
  expect(createdAt - typedAt).toBeGreaterThanOrEqual(700);
  await expect(page).toHaveURL(new RegExp(`/mi/${AID}/input$`));
});

test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: 'ignoreErrors' }); });
