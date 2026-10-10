/**
 * 화면 캡처(보드 대조용) — API 로 만든 보드 예 시나리오로 SC0 · SC2E · SC3R · SC4E 를 연다.
 */
import { expect, test } from '@playwright/test';
import { api, makeScenario, shot } from './helpers';

// 공유 개발 PC(2 CPU · 7GB, 다른 세션과 함께)에서 메모리 부족으로 브라우저 탭이 죽는 일이 있어 한 번만 다시 돌린다
test.describe.configure({ retries: 1 });

test('SC0 목록 · 행 상태 · 보내기 아이콘', async ({ page, request }) => {
  test.setTimeout(90_000);
  const done = await makeScenario(request, { title: 'A 커피 매장 하루 시나리오' });
  const draft = await makeScenario(request, { until: 'picked', title: 'B 병원 외래 동선 시나리오' });
  await page.goto('/scenario/legacy');
  const rowDone = page.locator(`[data-testid="sc0-row"][data-id="${done}"]`);
  const rowDraft = page.locator(`[data-testid="sc0-row"][data-id="${draft}"]`);
  await expect(rowDone).toBeVisible();
  await expect(rowDone.getByTestId('sc0-row-status')).toContainText('완료');
  await expect(rowDone.getByTestId('sc0-row-status')).toContainText('제안서에 아직 안 넣음');
  await expect(rowDone.getByRole('link', { name: '제안서로 보내기' })).toBeVisible();
  await expect(rowDraft.getByTestId('sc0-row-status')).toContainText('3 / 4 · 솔루션 · 제품 입력');
  await expect(rowDraft.getByRole('link', { name: '제안서로 보내기' })).toHaveCount(0);
  await expect(rowDone.getByTestId('sc0-row-start')).toHaveText('직접 입력');
  await expect(page.getByTestId('sc0-range')).toContainText(/\d+개 중 1–\d+/);
  await shot(page, 'SC0');
});

test('SC2E 타임라인 · SC3R 추천 · SC4E 장면 편집 캡처', async ({ page, request }) => {
  test.setTimeout(120_000); // 시나리오 2개를 만든다(생성 포함)
  const id = await makeScenario(request, { until: 'parsed', type: 'without' });
  await page.goto(`/scenario/${id}/timeline`);
  await expect(page.getByTestId('sc2e-head')).toContainText('· 시간대');
  await shot(page, 'SC2E');
  await api(request, 'PUT', `/scenarios/${id}/products`, { items: [{ ref: 'kb:model:mdl_LH55QMCEBGCXKR', family_id: 'fam_G000182628', model_code: 'LH55QMCEBGCXKR', label: 'Smart Signage QM55C', short: 'QM55C', qty: 3 }, { ref: 'custom:Kiosk KM24C', label: 'Kiosk KM24C', short: 'KM24C' }] });
  await page.goto(`/scenario/${id}/solutions`);
  await page.getByTestId('sc3-generate').click();
  await expect(page).toHaveURL(/\/solutions\/recommend$/);
  await expect(page.getByTestId('sc3r-row')).toHaveCount(4, { timeout: 30_000 });
  await shot(page, 'SC3R');
  const done = await makeScenario(request, {});
  const scenes = await api(request, 'GET', `/scenarios/${done}/scenes`);
  await page.goto(`/scenario/${done}/scenes/${scenes.items[1].id}`);
  await expect(page.getByTestId('sc4e-editor')).toBeVisible();
  await shot(page, 'SC4E');
});
