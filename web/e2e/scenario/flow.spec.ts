/**
 * 기본 흐름(§3.1) — SC1 → SC2 → SC3 → SC4G → SC4 → SC5, mock 모델.
 * AC5 · AC6(조감도 추가 토글) · AC16(등장인물 추출) · AC17(R2 → SC3) · AC40(장면 카드) · AC49(시트 3장).
 */
import { expect, test } from '@playwright/test';
import { RAW, shot } from './helpers';

// 공유 개발 PC(2 CPU · 7GB, 다른 세션과 함께)에서 메모리 부족으로 브라우저 탭이 죽는 일이 있어 한 번만 다시 돌린다
test.describe.configure({ retries: 1 });

test('새 시나리오 → 입력 → 솔루션 · 제품 → 생성 → 결과 → 보내기', async ({ page }) => {
  test.setTimeout(150_000);
  await page.goto('/scenario/legacy');                     // 이전 흐름 목록(새 흐름 목록 · Gate 는 /scenario · /scenario/new)
  await expect(page.getByRole('heading', { name: '공간 시나리오' })).toBeVisible();
  await page.getByTestId('sc0-new').click();
  await expect(page).toHaveURL(/\/scenario\/legacy\/new$/);

  // SC1
  await expect(page.getByTestId('sc1-with')).toHaveAttribute('aria-checked', 'true');
  const toggle = page.getByRole('button', { name: '조감도 추가' });
  await expect(toggle).toHaveAttribute('aria-pressed', 'false');
  await expect(page.getByTestId('sc1-aerial-tag')).toHaveText('선택 · 기본 꺼짐');
  await expect(page.getByTestId('sc1-aerial-opts')).toHaveCount(0);
  await shot(page, 'SC1');
  await toggle.click();
  await expect(page.getByTestId('sc1-aerial-tag')).toHaveText('켜짐');
  await expect(page.getByTestId('sc1-aerial-new')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('sc1-aerial-existing-sub')).toHaveText(/조감도 작업 \d+개에서 고르기/);
  await shot(page, 'SC1-aerial');
  await toggle.click();
  await page.getByTestId('sc1-next').click();

  // SC2
  await expect(page).toHaveURL(/\/scenario\/sc_[^/]+\/input$/);
  await expect(page.getByTestId('sc2-echo')).toHaveText('with 솔루션 · 솔루션 + 연관 제품 활용');
  await expect(page.getByTestId('sc2-next')).toBeDisabled();
  await page.getByTestId('sc2-text').fill(RAW);
  await expect(page.getByTestId('sc2-char')).toHaveCount(3, { timeout: 10_000 });
  await expect(page.getByTestId('sc2-chars')).toContainText('점장');
  await expect(page.getByTestId('sc2-chars')).toContainText('본사 마케팅 담당자');
  await shot(page, 'SC2');
  await page.getByTestId('sc2-next').click();

  // SC3
  await expect(page).toHaveURL(/\/solutions$/, { timeout: 30_000 });
  await expect(page.getByTestId('sc3-w')).toContainText('4개 장면으로 나눌 수 있겠네요');
  await expect(page.getByTestId('sc3-scenes')).toContainText('장면 1 · 오픈');
  await page.getByLabel('솔루션 입력').fill('MagicINFO');
  await page.getByRole('option', { name: /MagicINFO/ }).first().click();
  await expect(page.getByTestId('sc3-solutions-chip')).toHaveCount(1);
  await page.getByLabel('솔루션 입력').fill('SmartThings');
  await page.getByRole('option', { name: /SmartThings Pro/ }).first().click();
  await expect(page.getByTestId('sc3-solutions-chip')).toHaveCount(2);
  await page.getByLabel('제품 입력').fill('QM55C');
  await page.getByRole('option').first().click();
  await expect(page.getByTestId('sc3-products-chip')).toHaveCount(1);
  await page.getByLabel('제품 입력').fill('Kiosk KM24C');
  await page.getByLabel('제품 입력').press('Enter');
  await expect(page.getByTestId('sc3-products-chip')).toHaveCount(2);
  await shot(page, 'SC3');
  await page.getByTestId('sc3-generate').click();

  // SC4G → SC4
  await expect(page).toHaveURL(/\/(generate\/[^/]+|result)$/, { timeout: 20_000 });
  await expect(page).toHaveURL(/\/result$/, { timeout: 90_000 });
  await expect(page.getByTestId('sc4-scene')).toHaveCount(4);
  await expect(page.getByTestId('sc4-w')).toContainText('4개 장면으로 시나리오를 구성했습니다');
  await expect(page.getByTestId('sc4-scene').first().getByTestId('sc4-scene-title')).toContainText('오픈 — ');
  await expect(page.getByTestId('sc4-img-make').first()).toHaveText('이미지 생성');
  await shot(page, 'SC4');

  // SC5
  await page.getByTestId('sc4-send').click();
  await expect(page).toHaveURL(/\/send$/);
  await expect(page.getByTestId('sc5-sheet')).toHaveCount(3);
  await expect(page.getByTestId('sc5-w')).toContainText('장면 4개를 공간 기준으로 묶어 시트 3장으로 나눴어요');
  await expect(page.getByTestId('sc5-export-pptx')).toContainText('PPTX · 시트 3장');
  await expect(page.getByTestId('sc5-export-zip')).toBeDisabled();
  await shot(page, 'SC5');
});
