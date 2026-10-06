/**
 * 기본 흐름(§3.1) — BE1 → BE2 → BE3 → BE4 → BE5G → BE5 → BE6, mock 모델 · 실제 KB · image 렌더 API(mock).
 * AC 6 · 22 · 23 · 24 · 25 · 30 · 40 · 45 · 56 일부.
 */
import { expect, test } from '@playwright/test';
import { DESC, shot } from './helpers';

test('새 조감도 → 공간 → 제품 → 가구 → 배치 → 3D 생성 → 결과 → 내보내기', async ({ page }) => {
  test.setTimeout(240_000);
  await page.goto('/birdseye');
  await expect(page.getByRole('heading', { name: /조감도 작업/ })).toBeVisible();
  await shot(page, 'BE0');
  await page.getByRole('link', { name: '새 조감도 만들기' }).click();
  await expect(page).toHaveURL(/\/birdseye\/new$/);

  // BE1
  await expect(page.getByTestId('be1-chip-store_lobby')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByLabel('면적')).toHaveAttribute('placeholder', '120');
  await expect(page.getByLabel('층고')).toHaveAttribute('placeholder', '4.5');
  await expect(page.getByTestId('be1-next')).toBeDisabled();
  await page.getByLabel('공간 설명').fill(DESC);
  await page.getByLabel('층고').fill('30');
  await expect(page.getByText('층고는 1.8~20 m 사이로 적어 주세요')).toBeVisible();
  await page.getByLabel('층고').fill('');
  await shot(page, 'BE1');
  await page.getByTestId('be1-next').click();

  // BE2
  await expect(page).toHaveURL(/\/birdseye\/be_[^/]+\/products$/, { timeout: 15_000 });
  await expect(page.getByTestId('be-w')).toContainText('로비 공간을 파악했습니다.', { timeout: 30_000 });
  await expect(page.getByTestId('be2-chips')).toContainText('120평 · 층고 4.5m');
  await expect(page.getByTestId('be2-chips')).toContainText('중앙 기둥 2개');
  await expect(page.getByTestId('be2-next')).toBeDisabled();
  const input = page.getByLabel('제품명 입력');
  await input.fill('the w');
  await expect(page.getByTestId('be2-results-head')).toHaveText('"the w" 검색 결과 · Enter로 추가');
  await expect(page.getByText('추가 ↵')).toBeVisible();
  await shot(page, 'BE2-search');
  await input.press('Enter');
  await expect(page.getByTestId('be2-token')).toHaveCount(1, { timeout: 15_000 });
  for (const q of ['OH55', 'Flip Pro']) {
    await input.fill(q);
    await expect(page.getByTestId('be2-results-head')).toBeVisible();
    await input.press('Enter');
  }
  await expect(page.getByTestId('be2-token')).toHaveCount(3, { timeout: 20_000 });
  await expect(page.getByTestId('be-dock')).toContainText('3개 추가됨 · 2 / 5');
  await shot(page, 'BE2');
  await page.getByTestId('be2-next').click();

  // BE3
  await expect(page).toHaveURL(/\/furniture$/);
  await expect(page.getByTestId('be3-cards').getByRole('button')).toHaveCount(4, { timeout: 30_000 });
  await expect(page.getByTestId('be3-cards').locator('[aria-pressed="true"]')).toHaveCount(3);
  await expect(page.getByTestId('be3-selected')).toContainText('기둥 랩핑 프레임 ×2');
  await shot(page, 'BE3');
  await page.getByTestId('be3-next').click();

  // BE4
  await expect(page).toHaveURL(/\/layout$/);
  await expect(page.getByTestId('be4-canvas')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('be-w')).toContainText('배치안입니다.', { timeout: 30_000 });
  await expect(page.getByTestId('be4-tone-warm_wood')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('be4-view-aerial45')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('be4-canvas')).toContainText('120평 · 4.5m');
  await expect(page.getByTestId('be4-canvas')).toContainText('기둥 랩핑 ×2');
  await shot(page, 'BE4');
  await page.getByTestId('be4-render').click();

  // BE5G → BE5
  await expect(page).toHaveURL(/\/render\/job_/, { timeout: 15_000 });
  await expect(page.getByTestId('be5g-progress')).toBeVisible();
  await expect(page.getByTestId('be5g-steps')).toContainText('공간 구조');
  await expect(page.getByTestId('be5g-preview')).toBeVisible({ timeout: 60_000 });
  await shot(page, 'BE5G');
  await expect(page).toHaveURL(/\/result\?cut=bec_/, { timeout: 180_000 });
  await expect(page.getByTestId('be-w')).toContainText('3D 조감도가 완성되었습니다. 웜 우드 톤, 45° 조감 시점이며 제품 3종과 가구');
  await expect(page.getByTestId('be5-tags')).toContainText('조감 45°');
  await expect(page.getByTestId('be5-tags')).toContainText('웜 우드');
  await shot(page, 'BE5');

  // BE6
  await page.getByTestId('be5-export').click();
  await expect(page).toHaveURL(/\/export$/);
  await expect(page.getByTestId('be6-images')).toContainText('조감 45° · 주간');
  await expect(page.getByTestId('be6-qty')).toContainText('제품');
  await expect(page.getByTestId('be6-map')).toContainText('BV-A');
  await expect(page.getByTestId('be6-map')).toContainText('SM-B');
  await expect(page.getByTestId('be6-filename')).toHaveValue(/_조감도_v1$/);
  await shot(page, 'BE6');
});
