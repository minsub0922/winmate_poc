/**
 * 경쟁사 분석 갈래 — CA2Q(묻기 1: 건너뛰기 · 답하기) · CA1R(정의서 · 덧붙일 내용) · CA3C(기준 바꾸기) · 중지 띠 · CA0 업데이트 배너 · CA4D 더 찾기.
 * AC-CA-05 · 08 · 11 · 12 · 29 · 33 · 40 · 48 · 49 · 50 화면 쪽. 실제 competitor · mock 모델(공유 데이터라 만든 작업만 id 로 본다).
 */
import { expect, test } from '@playwright/test';
import { A_TEXT, CA_ID, SETUP_MS, api, backendDown, budget, seedConfirming, seedDone, shot, uniq, waitStatus } from './helpers';

test.describe.configure({ timeout: SETUP_MS });   // 준비(page · 첫 요청) 시간 — 본문은 budget(ms) 로 더한다

test.beforeEach(async ({ request }) => {
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
});

const AMBIGUOUS = '매장 메뉴보드 사이니지';

async function startFree(page: import('@playwright/test').Page, text: string) {
  await page.goto('/competitor/new');
  await page.getByLabel('고객 · 사업 설명').fill(text);
  await expect(page).toHaveURL(new RegExp(`/competitor/${CA_ID.source}/input$`), { timeout: 6_000 });
  await page.getByRole('button', { name: '경쟁사 찾기' }).click();
  return page.url().match(CA_ID)![0];
}

test('CA2Q 묻기 1 → 건너뛰기 — 업종 기준으로 찾기', async ({ page, request }) => {
  budget(90_000);
  const id = await startFree(page, AMBIGUOUS);
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/ask$`), { timeout: 30_000 });
  await expect(page.getByRole('heading', { name: '어느 고객사, 어느 지역인가요?' })).toBeVisible();
  await expect(page.getByText('입력에서 업종(외식 · 카페)과 제품(메뉴보드 사이니지)은 읽었지만 고객사와 장소가 없어요. 알려 주면 지역 경쟁사까지 찾아요.')).toBeVisible();
  const strip = page.getByRole('group', { name: '입력에서 읽은 것' });
  await expect(strip.locator('.ca-slot__part')).toHaveCount(2);                 // 업종 · 제품 `일부`
  await expect(strip).toContainText('2 / 4');
  const answer = page.getByRole('button', { name: '답하고 찾기' });
  await expect(answer).toBeDisabled();                                          // AC-CA-11
  await shot(page, 'ca2q-ask');
  await page.getByRole('button', { name: '건너뛰기 — 업종 기준으로 찾기' }).click();
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/candidates$`), { timeout: 30_000 });
  await expect(page.getByRole('list', { name: '확인 권장' })).toContainText('업종 기준');   // AC-CA-12
  await expect(page.getByRole('list', { name: '확인 권장' })).toContainText('업종 확인');
  const a = await api(request, 'GET', `/analyses/${id}`);
  expect(a.chips.map((c: any) => c.label)).toEqual(expect.arrayContaining(['업종 기준', '업종 확인']));
  await shot(page, 'ca2-industry-basis');
});

test('CA2Q 묻기 1 → 고객사 답하고 찾기', async ({ page, request }) => {
  budget(90_000);
  const id = await startFree(page, AMBIGUOUS);
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/ask$`), { timeout: 30_000 });
  await page.getByLabel('고객사').fill('A 커피 프랜차이즈');
  await page.getByRole('button', { name: '답하고 찾기' }).click();
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/candidates$`), { timeout: 30_000 });
  const a = await api(request, 'GET', `/analyses/${id}`);
  expect(a.slots.customer.value).toBe('A 커피 프랜차이즈');
  expect(a.slots.customer.origin).toBe('answer');
  await expect(page.getByRole('group', { name: '입력에서 읽은 것' })).toContainText('A 커피 프랜차이즈');
});

test('CA1R 정의서에서 → 덧붙일 내용(꼭 넣을 곳) → 찾기', async ({ page, request }) => {
  budget(120_000);
  const tag = uniq();
  const rq = await (await request.post('/api/requirements/v1/requirements', {
    data: { form: { project_name: `A 커피 프랜차이즈 매장 리뉴얼 ${tag}`, customer_name: 'A 커피 프랜차이즈' } },
  })).json();
  test.skip(!rq?.id, '요구사항 서비스에 정의서를 만들 수 없어요');
  const k1 = await request.patch(`/api/requirements/v1/requirements/${rq.id}/draft`, { data: { ops: [{ op: 'add_keyman', name: '본사 IT' }] } });
  expect(k1.ok(), await k1.text()).toBeTruthy();
  const km = ((await k1.json()).form?.keymen ?? []).at(-1)?.id;
  expect(km).toBeTruthy();
  const ops = ['본사에서 전 매장 메뉴 콘텐츠를 일괄 배포', '매장별로 가격을 다르게 표시', '전기료 절감'].map((text) => ({ op: 'add_item', keyman_id: km, text }));
  const pr = await request.patch(`/api/requirements/v1/requirements/${rq.id}/draft`, { data: { ops } });
  expect(pr.ok(), await pr.text()).toBeTruthy();
  const sv = await request.post(`/api/requirements/v1/requirements/${rq.id}/save`, { data: { reason: 'direct' } });
  expect(sv.ok(), await sv.text()).toBeTruthy();

  await page.goto(`/competitor/new?input=requirements&rq=${rq.id}`);
  await expect(page.getByRole('tab', { name: '고객 요구사항에서' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText(/정의서 고르기/)).toBeVisible();
  const radio = page.getByRole('radio', { name: new RegExp(`매장 리뉴얼 ${tag}`) });
  await expect(radio).toHaveAttribute('aria-checked', 'true');
  const strip = page.getByRole('group', { name: '정의서에서 채운 것' });
  await expect(strip).toContainText('고객사·A 커피 프랜차이즈', { timeout: 15_000 });
  await page.getByLabel('덧붙일 내용').fill('ZZ 사이니지는 꼭 넣고 YY 광고는 빼');
  await shot(page, 'ca1r-requirements');
  await page.getByRole('button', { name: '경쟁사 찾기' }).click();
  await expect(page).toHaveURL(new RegExp(`/competitor/${CA_ID.source}/(finding|candidates|ask)$`), { timeout: 10_000 });
  const id = page.url().match(CA_ID)![0];
  await expect(page).toHaveURL(new RegExp(`/competitor/${id}/candidates$`), { timeout: 30_000 });
  const zz = page.locator('.ca-cand', { hasText: 'ZZ 사이니지' });              // AC-CA-05 꼭 넣을 곳 = 켜짐 · 고정
  await expect(zz.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
  await expect(page.locator('.ca-cand', { hasText: 'YY 광고' })).toHaveCount(0);
  const a = await api(request, 'GET', `/analyses/${id}`);
  expect(a.input_mode).toBe('requirements');
  expect(a.requirements_id).toBe(rq.id);
  const links = await (await request.get(`/api/requirements/v1/requirements/${rq.id}/links`)).json();
  const items = Array.isArray(links) ? links : links.items;
  expect(items.some((l: any) => l.ref_id === id)).toBeTruthy();
});

test('CA3C 기준 바꾸기 → 이 기준으로 분석(다시 판정)', async ({ page, request }) => {
  budget(150_000);
  const a = await seedDone(request);
  await page.goto(`/competitor/${a.id}/criteria`);
  await expect(page.getByRole('heading', { name: '무엇을 기준으로 비교할까요?' })).toBeVisible();
  const group = page.getByRole('group', { name: '비교 기준 6' });
  await expect(group.locator('.ca-crow')).toHaveCount(6);
  await expect(page.getByText(/켜진 기준\s*6\s*\/ 6/)).toBeVisible();
  await page.getByRole('switch', { name: '전기료 끄기' }).click();
  await expect(page.getByText(/켜진 기준\s*5\s*\/ 6/)).toBeVisible();                 // AC-CA-29
  await page.getByRole('button', { name: '본사 일괄 배포 중요도 3' }).click();
  await expect(page.getByRole('group', { name: '본사 일괄 배포 중요도 3 / 5' })).toBeVisible();
  await page.getByRole('button', { name: /가격대 순서 옮기기/ }).press('ArrowUp');
  const sugg = page.getByRole('button', { name: /추천 기준 .* 더하기/ }).first();
  if (await sugg.count()) await sugg.click();
  await shot(page, 'ca3c-criteria');
  await page.getByRole('button', { name: '이 기준으로 분석' }).click();
  await expect(page).toHaveURL(new RegExp(`/competitor/${a.id}/(run|result)$`));
  await expect(page).toHaveURL(new RegExp(`/competitor/${a.id}/result$`), { timeout: 60_000 });
  const crit = await api(request, 'GET', `/analyses/${a.id}/criteria`);
  expect(crit.mode).toBe('pin');
  expect(crit.items.find((c: any) => c.name === '전기료').enabled).toBe(false);
  const vers = await api(request, 'GET', `/analyses/${a.id}/versions`);
  expect(vers.items[0].kind).toBe('rejudge');
});

test('CA4 중지 띠 · 회색 행 → 이어서 분석', async ({ page, request }) => {
  budget(150_000);
  const a = await seedDone(request);
  // 중지 상태 화면(부분 결과) — 서버 결과를 받아 두 곳만 끝난 모양으로 바꿔 그린다(중지 자체는 pytest test_ac33)
  await page.route(`**/api/competitor/v1/analyses/${a.id}/result**`, async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    body.status = 'stopped';
    body.partial = { analyzing: false, stopped: true, done: 2, total: 4, text: '분석을 멈췄어요 · 2곳만 결과가 있어요' };
    body.competitors = body.competitors.map((c: any, i: number) => (i < 2 ? c : { ...c, state: 'skipped', state_label: '분석 안 함', positioning: '' }));
    await route.fulfill({ response: res, json: body });
  });
  await page.goto(`/competitor/${a.id}/result`);
  await expect(page.getByText('분석을 멈췄어요 · 2곳만 결과가 있어요')).toBeVisible();
  const rows = page.getByRole('list', { name: '경쟁사' }).getByRole('listitem');
  await expect(rows.nth(2)).toContainText('분석 안 함');
  await expect(rows.nth(2)).toHaveAttribute('aria-disabled', 'true');
  await shot(page, 'ca4-stopped');
  await page.unroute(`**/api/competitor/v1/analyses/${a.id}/result**`);
  await page.getByRole('button', { name: '이어서 분석' }).click();
  await expect(page).toHaveURL(new RegExp(`/competitor/${a.id}/(run|result)$`));
  await waitStatus(request, a.id, ['done']);
});

test('CA0 업데이트 배너 → 다시 분석(바뀐 경쟁사만) · CA4D 더 찾기', async ({ page, request }) => {
  budget(180_000);
  const a = await seedDone(request);
  await api(request, 'POST', `/analyses/${a.id}/recheck`);
  const upd = await waitStatus(request, a.id, ['upd'], 60_000);                      // AC-CA-49
  expect(upd.status_label).toBe('업데이트 필요');
  await page.goto('/competitor');
  const row = page.locator(`[data-id="${a.id}"]`);
  await expect(row).toContainText('업데이트 필요');
  await expect(row).toContainText(/완료 · 경쟁사 [A-F] 신제품 \d{4}\.\d{2}/);
  await expect(row.getByRole('link', { name: '상세 보기' })).toBeVisible();
  await expect(page.getByText(/건은 다시 분석을 권해요\./)).toBeVisible();
  await expect(page.locator('.ca-upd__text')).toContainText(/경쟁사 [A-F] 가 \d{4}\.\d{2} 신제품을 냈어요 — /);
  await shot(page, 'ca0-upd-banner');

  // 결과 화면의 다시 분석 띠(이 작업) → 바뀐 경쟁사만(AC-CA-50)
  await page.goto(`/competitor/${a.id}/result`);
  await expect(page.getByText('다시 분석을 권해요.')).toBeVisible();
  await page.locator('.ca-band').getByRole('button', { name: '다시 분석' }).click();
  await expect(page).toHaveURL(new RegExp(`/competitor/${a.id}/(run|result)$`));
  const done = await waitStatus(request, a.id, ['done'], 90_000);
  expect(done.version).toBe(2);
  const vers = await api(request, 'GET', `/analyses/${a.id}/versions`);
  expect(vers.items[0].kind).toBe('changed_only');

  // CA4D 이 경쟁사 더 찾기(AC-CA-40)
  const res = await api(request, 'GET', `/analyses/${a.id}/result`);
  await page.goto(`/competitor/${a.id}/competitors/${res.competitors[0].id}`);
  await page.getByRole('button', { name: '이 경쟁사 더 찾기' }).click();
  await expect.poll(async () => (await api(request, 'GET', `/analyses/${a.id}/versions`)).items[0].kind, { timeout: 60_000 }).toBe('research');
});

test('CA0 MI 작업의 경쟁사에서 — 고르기 시트', async ({ page }) => {
  await page.goto('/competitor');
  await page.getByRole('button', { name: /MI 작업의 경쟁사에서/ }).click();
  const dlg = page.getByRole('dialog', { name: 'MI 작업의 경쟁사에서 시작' });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByRole('list', { name: '경쟁사가 있는 MI 작업' })).toBeVisible();
  await shot(page, 'ca0-mi-pick');
  await page.keyboard.press('Escape');
  await expect(dlg).toBeHidden();
});

test('CA1 새로 시작 · 비어 있는 칩 · 2 / 4(AC-CA-02)', async ({ page }) => {
  await page.goto('/competitor/new');
  await page.getByLabel('고객 · 사업 설명').fill('카페 메뉴보드 사이니지 교체');
  const strip = page.getByRole('group', { name: '입력에서 읽은 것' });
  await expect(strip).toContainText('고객사·비어 있음', { timeout: 15_000 });
  await expect(strip).toContainText('장소·비어 있음');
  await expect(strip.locator('[data-slot="product"] .ca-slot__part')).toHaveText('일부');
  await expect(strip).toContainText('2 / 4');
  await shot(page, 'ca1-partial');
  // 정리: 만든 draft 는 지운다
  const m = page.url().match(CA_ID);
  if (m) await page.request.delete(`/api/competitor/v1/analyses/${m[0]}`);
});

test('A 커피 결과 — 분석 결과 없는 경쟁사 상세는 안내', async ({ page, request }) => {
  const a = await seedConfirming(request, A_TEXT);
  await page.goto(`/competitor/${a.id}/competitors/cmp_none`);
  await expect(page.getByText('이 경쟁사는 아직 분석 결과가 없어요')).toBeVisible();
});
