/**
 * 결과 뒤 화면 — BE5V 시점 · 조명(AC48), BE5Z 존 포인트(AC52~55 일부), BE0 목록 · 복제(AC1 꼴 · AC4), UC_BE.
 * 결과 컷은 API(image 렌더 mock)로 만든다.
 */
import { expect, test } from '@playwright/test';
import { api, makeResult, shot } from './helpers';

test('BE5V 새로 만들 컷 수 → 생성 · BE5Z 존 포인트 → 동선 번호 · 시트 레이아웃 · 포인트 추가', async ({ page, request }) => {
  test.setTimeout(240_000);
  const { id } = await makeResult(request);

  // BE5V — 입구 시점 + {대표 제품} 정면, 야간 → 2컷, 도입 전 컷도 → 4컷
  await page.goto(`/birdseye/${id}/views`);
  await expect(page.getByTestId('be5v-cuts')).toContainText('조감 45° · 주간', { timeout: 20_000 });
  await expect(page.getByTestId('be5v-n')).toHaveText('0');
  await expect(page.getByTestId('be5v-make')).toBeDisabled();
  await page.getByTestId('be5v-entrance').click();
  await page.getByTestId('be5v-front').click();
  await page.getByTestId('be5v-light-night').click();
  await expect(page.getByTestId('be5v-light-day')).toHaveAttribute('aria-pressed', 'false');
  await expect(page.getByTestId('be5v-n')).toHaveText('2');
  await expect(page.getByTestId('be5v-make')).toHaveText(/선택한 2컷 생성/);
  await page.getByRole('switch', { name: '도입 전 컷도' }).click();
  await expect(page.getByTestId('be5v-n')).toHaveText('4');
  await shot(page, 'BE5V');
  await page.getByRole('switch', { name: '도입 전 컷도' }).click();
  await expect(page.getByTestId('be5v-n')).toHaveText('2');
  await page.getByTestId('be5v-make').click();
  await expect(page).toHaveURL(/\/render\/job_/, { timeout: 30_000 });
  await expect(page.getByTestId('be5g-progress')).toBeVisible({ timeout: 30_000 });
  await expect.poll(async () => (await api(request, 'GET', `/birdseyes/${id}/cuts`)).filter((c: any) => ['done', 'check'].includes(c.status)).length,
    { timeout: 150_000, intervals: [2000] }).toBe(3);

  // BE5Z — 자동 존 포인트
  await page.goto(`/birdseye/${id}/zones`);
  await expect(page.getByTestId('be5z-pin-1')).toBeVisible({ timeout: 40_000 });
  const n0 = await page.locator('[data-testid^="be5z-card-"]').count();
  expect(n0).toBeGreaterThanOrEqual(2);
  await expect(page.getByTestId('be5z-preview')).toContainText('ZP-A');
  await expect(page.getByTestId('be5z-preview')).toContainText(`번호 콜아웃 · 포인트 ${n0}곳`);
  await expect(page.getByTestId('be5z-preview')).toContainText('연결된 제안서 없음');
  await page.getByTestId('be5z-renumber').click();
  await expect(page.getByTestId('be5z-pin-1')).toBeVisible();
  await page.getByTestId('be5z-layout-ZP-B').click();
  await expect(page.getByTestId('be5z-preview')).toContainText('존 확대 컷');
  await expect(page.getByTestId('be5z-layout-ZP-B')).toHaveAttribute('aria-pressed', 'true');
  // 존 이름 ≤ 14자 · 문구 ≤ 60자(AC55)
  const card1 = page.getByTestId('be5z-card-1');
  await card1.getByRole('button').first().click();
  await expect(card1.getByLabel('존 이름')).toHaveAttribute('maxlength', '14');
  await expect(card1.getByLabel('포인트 문구')).toHaveAttribute('maxlength', '60');
  await shot(page, 'BE5Z');
  // 빈 곳을 눌러 포인트 추가(AC54)
  const img = page.getByTestId('be5z-image');
  const bx = (await img.boundingBox())!;
  await page.mouse.click(bx.x + bx.width * 0.12, bx.y + bx.height * 0.88);
  await expect(page.locator('[data-testid^="be5z-card-"]')).toHaveCount(n0 + 1, { timeout: 10_000 });
  await page.getByTestId('be5z-send').click();
  await expect(page).toHaveURL(new RegExp(`/birdseye/${id}/export\\?map=ZP$`));
  await expect(page.getByTestId('be6-map')).toContainText('ZP-B');
});

test('BE0 목록 — 상태 필터 · 행 메뉴 「복제해서 새 시안」 → BE4 · 유스케이스 맵', async ({ page, request }) => {
  test.setTimeout(150_000);
  const title = `e2e 복제 원본 ${Date.now()}`;
  const { id } = await makeResult(request, title);
  await page.goto('/birdseye');
  await page.getByPlaceholder('작업 · 고객사 · 공간 검색').fill(title);
  const row = page.getByTestId(`be0-row-${id}`);
  await expect(row).toBeVisible({ timeout: 15_000 });
  await expect(row).toContainText('완료');
  await expect(row).toContainText('시점 1');
  await expect(row.getByRole('link', { name: '열기' })).toBeVisible();
  await expect(row).toContainText('아직 없음');
  await page.getByTestId('be0-tab-done').click();
  await expect(row).toBeVisible();
  await page.getByTestId('be0-tab-in_progress').click();
  await expect(row).toBeHidden();
  await page.getByTestId('be0-tab-all').click();
  await row.getByRole('button', { name: '작업 메뉴' }).click();
  await page.getByRole('menuitem', { name: '복제해서 새 시안' }).click();
  await expect(page).toHaveURL(/\/birdseye\/be_[^/]+\/layout$/, { timeout: 15_000 });
  const newId = /\/birdseye\/(be_[^/]+)\/layout$/.exec(page.url())![1];
  expect(newId).not.toBe(id);
  const cl = await api(request, 'GET', `/birdseyes/${newId}`);
  expect(cl.cloned_from).toBe(id);
  expect(cl.primary_cut_id ?? null).toBeNull();
  await expect(page.getByTestId('be4-canvas')).toBeVisible({ timeout: 20_000 });

  await page.goto('/birdseye/uc');
  await expect(page.getByTestId('be-uc')).toContainText('공간 조감도 생성 — 유스케이스 맵');
  await shot(page, 'UC_BE');
});
