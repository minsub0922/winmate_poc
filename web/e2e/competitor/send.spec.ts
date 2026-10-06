/**
 * CA5 저장 · 보내기 — MI 합치기(실제 mi) · 제안서 Why Samsung(묻기 2 · 넘김 기록) · Storyboard 비교 기준 · 리포트.
 * 제안서 · Storyboard 쪽 API 는 이번 배치에서 다른 세션이 만들고 있어 page.route 로 흉내 낸다(요청 모양만 본다).
 * AC-CA-42 · 43 · 44 · 45 · 54 화면 쪽.
 */
import { expect, test } from '@playwright/test';
import { REAL, SETUP_MS, api, backendDown, budget, seedDone, shot } from './helpers';

test.describe.configure({ timeout: SETUP_MS });   // 준비(page · 첫 요청) 시간 — 본문은 budget(ms) 로 더한다

test.beforeEach(async ({ request }) => {
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
});

const PROPOSALS = {
  items: [{ id: 'prp_E2E0000000000000000000000', title: 'A 커피 프랜차이즈 메뉴보드 제안', short_title: 'A 커피 제안', customer_name: 'A 커피 프랜차이즈',
    type_label: '표준', status_label: '작성 중', route: '/proposal/prp_E2E0000000000000000000000' }],
  next_cursor: null, counts: {}, total: 1,
};
const STORYBOARDS = {
  items: [{ id: 'sb_E2E00000000000000000000000', title: 'A 커피 매장 Storyboard', customer_name: 'A 커피 프랜차이즈', step_label: '기획 질의',
    status_label: '진행 중', route: '/storyboard/sb_E2E00000000000000000000000' }],
  next_cursor: null,
};

test('제안서 Why Samsung — 익명 켜짐: 묻지 않고 익명 넘김 · 기록 delivered', async ({ page, request }) => {
  budget(150_000);
  const a = await seedDone(request);
  let imported: any = null;
  await page.route('**/api/proposal/v1/proposals?*', (r) => r.fulfill({ json: PROPOSALS }));
  await page.route('**/api/proposal/v1/proposals/*/imports', async (r) => {
    imported = r.request().postDataJSON();
    await r.fulfill({ status: 202, json: { job_id: 'job_E2E', status: 'queued', kind: 'proposal.import', proposal_id: PROPOSALS.items[0].id, import_id: 'imp_E2E', section_key: 'why' } });
  });
  await page.route('**/api/proposal/v1/proposals/prp_E2E*', (r) => r.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: '시험용', details: {} } } }));
  await page.goto(`/competitor/${a.id}/send`);
  await page.getByRole('button', { name: /제안서 Why Samsung · 경쟁 비교 시트로/ }).click();
  const sheet = page.getByRole('dialog', { name: '어느 제안서로 보낼까요?' });
  await expect(sheet).toBeVisible();
  await expect(sheet.getByText('새 제안서로 시작')).toBeVisible();
  await shot(page, 'ca5-proposal-pick');
  await sheet.getByRole('listitem').filter({ hasText: 'A 커피 프랜차이즈 메뉴보드 제안' }).click();
  await expect(page).toHaveURL(/\/proposal\/prp_E2E0+\/sections\/why$/, { timeout: 15_000 });
  expect(imported).toMatchObject({ section_key: 'why', via: 'handoff', source: { feature: 'competitor', ref_id: a.id, version: 1 } });
  const hs = await api(request, 'GET', `/analyses/${a.id}/handoffs`);
  const h = hs.items.find((x: any) => x.target === 'proposal_why');
  expect(h.status).toBe('delivered');
  expect(h.target_id).toBe(PROPOSALS.items[0].id);
  expect(imported.source.handoff_id).toBe(h.id);
  // proposal 이 읽는 ProposalHandoff — 익명(AC-CA-53)
  const ph = await api(request, 'GET', `/analyses/${a.id}/proposal-handoff?section=why&handoff_id=${h.id}`);
  expect(ph.items.map((i: any) => i.key)).toEqual(['CM', 'ST']);
  for (const n of REAL) expect(JSON.stringify(ph)).not.toContain(n);
});

test('제안서 Why Samsung — 익명 꺼짐: 묻기 2 → 실명으로 보내기 · named ProposalHandoff', async ({ page, request }) => {
  budget(150_000);
  const a = await seedDone(request);
  await page.route('**/api/proposal/v1/proposals?*', (r) => r.fulfill({ json: PROPOSALS }));
  await page.route('**/api/proposal/v1/proposals/*/imports', (r) => r.fulfill({ status: 202, json: { job_id: 'job_E2E', status: 'queued', kind: 'proposal.import' } }));
  await page.route('**/api/proposal/v1/proposals/prp_E2E*', (r) => r.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: '시험용', details: {} } } }));
  await page.goto(`/competitor/${a.id}/send`);
  await page.getByRole('switch', { name: '고객 제출물엔 익명으로 표기' }).click();
  await expect(page.getByText('실명 표기 · 보낼 때 한 번 더 물어요')).toBeVisible();
  await page.getByRole('button', { name: /제안서 Why Samsung · 경쟁 비교 시트로/ }).click();
  const ask = page.getByRole('dialog', { name: '경쟁사 실명을 고객 제출물에 넣을까요?' });
  await expect(ask).toBeVisible();                                                    // AC-CA-44 묻기 2
  await expect(ask.getByRole('button', { name: '익명으로 보내기' })).toBeVisible();
  await shot(page, 'ca5-ask-real-names');
  await ask.getByRole('button', { name: '실명으로 보내기' }).click();
  await page.getByRole('dialog', { name: '어느 제안서로 보낼까요?' }).getByRole('listitem').filter({ hasText: 'A 커피 프랜차이즈 메뉴보드 제안' }).click();
  await expect(page).toHaveURL(/\/proposal\/prp_E2E0+\/sections\/why$/, { timeout: 15_000 });
  const h = (await api(request, 'GET', `/analyses/${a.id}/handoffs`)).items.find((x: any) => x.target === 'proposal_why');
  expect(h.confirmations.real_names).toBe(true);
  const ph = await api(request, 'GET', `/analyses/${a.id}/proposal-handoff?section=why&named=true&handoff_id=${h.id}`);   // AC-CA-54
  expect(ph.named).toBe(true);
  expect(REAL.some((n) => JSON.stringify(ph).includes(n))).toBeTruthy();
  await api(request, 'PATCH', `/analyses/${a.id}`, { anonymize: true });
});

test('Storyboard 비교 기준으로 — 익명 묶음 올리기 → SB1Q3', async ({ page, request }) => {
  budget(150_000);
  const a = await seedDone(request);
  let body: any = null;
  await page.route('**/api/storyboard/v1/storyboards?*', (r) => r.fulfill({ json: STORYBOARDS }));
  await page.route('**/api/storyboard/v1/storyboards/*/imports/competitor', async (r) => { body = r.request().postDataJSON(); await r.fulfill({ json: { question: null, stored: true } }); });
  await page.route('**/api/storyboard/v1/storyboards/sb_E2E*', (r) => (r.request().url().includes('/imports/') ? r.fallback() : r.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: '시험용', details: {} } } })));
  await page.goto(`/competitor/${a.id}/send`);
  await page.getByRole('button', { name: /Storyboard 비교 기준으로/ }).click();
  const sheet = page.getByRole('dialog', { name: '어느 Storyboard 의 비교 기준으로 넣을까요?' });
  await sheet.getByRole('listitem').filter({ hasText: 'A 커피 매장 Storyboard' }).click();
  await expect(page).toHaveURL(/\/storyboard\/sb_E2E0+\/planning\/3$/, { timeout: 15_000 });
  expect(body.competitors).toEqual(['경쟁사 A', '경쟁사 B', '경쟁사 C', '경쟁사 D']);       // AC-CA-45 익명 글자
  expect(body.criteria.map((c: any) => c.name)).toEqual(['본사 일괄 배포', '매장별 가격 차등', '전기료', '인건비 절감', '가격대', '레퍼런스 · AS']);
  expect(body.criteria[0].importance).toBe('5');
  for (const n of REAL) expect(JSON.stringify(body)).not.toContain(n);
  const h = (await api(request, 'GET', `/analyses/${a.id}/handoffs`)).items.find((x: any) => x.target === 'storyboard');
  expect(h.status).toBe('delivered');
});

test('MI 작업에 합치기 — 실제 mi imports/competitor → MI 결과 경쟁사 탭', async ({ page, request }) => {
  budget(180_000);
  const mi = await request.get('/api/mi/v1/info').catch(() => null);
  test.skip(!mi || !mi.ok(), 'mi 서비스가 꺼져 있어요');
  const a = await seedDone(request);
  await page.goto(`/competitor/${a.id}/send`);
  const card = page.getByRole('button', { name: /Market Intelligence 작업에 합치기/ });
  await expect(card).toBeEnabled();
  await card.click();
  await expect(page).toHaveURL(/\/mi\/mi_[0-9A-Z]+\/(result\?tab=competitor|revise)/, { timeout: 120_000 });   // AC-CA-42
  const h = (await api(request, 'GET', `/analyses/${a.id}/handoffs`)).items.find((x: any) => x.target === 'mi');
  expect(h.status).toBe('delivered');
  const lst = await api(request, 'GET', '/analyses?limit=100');
  expect(lst.items.find((x: any) => x.id === a.id)?.sent_label).toContain('MI 작업');
});
