/**
 * 화면 캡처 — 홈 · 팝오버 4종(작업 없음/있음) · 상세 시트 탭 6 · 스텝바 · 제품 입력창.
 * 결과: e2e/shell/__screens__/*.png (보드 webapp1 과 눈으로 비교).
 */
import { expect, test, type Page } from '@playwright/test';
import { setupShell } from './fixtures/mock';

const shot = (page: Page, name: string) => page.screenshot({ path: `e2e/shell/__screens__/${name}.png` });

test.describe('화면 캡처', () => {
  test.beforeEach(async ({ page }) => { await setupShell(page); });

  test('홈', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('민섭님');
    await expect(page.locator('[data-recent]').first()).toBeVisible();
    await page.waitForTimeout(300);
    await shot(page, 'home');
  });

  test('팝오버 4종(작업 없음)', async ({ page }) => {
    await page.goto('/?pop=product&node=fam_G000182628');
    await expect(page.locator('[data-model]')).toHaveCount(7);
    await page.waitForTimeout(200);
    await shot(page, 'pop-product');
    await page.goto('/?pop=solution');
    await expect(page.locator('[data-solution]')).toHaveCount(11);
    await shot(page, 'pop-solution');
    await page.goto('/?pop=image&q=' + encodeURIComponent('카페 메뉴보드'));
    await expect(page.getByRole('dialog', { name: '이미지 검색' }).locator('.wm-tilewrap')).toHaveCount(6);
    await expect(page.locator('aside[aria-label="이미지 정보"]')).toContainText('출처 페이지');
    await page.waitForTimeout(300);
    await shot(page, 'pop-image');
    await page.goto('/?pop=case&q=' + encodeURIComponent('프랜차이즈 메뉴보드'));
    await expect(page.locator('[data-case-card]')).toHaveCount(3);
    await page.waitForTimeout(300);
    await shot(page, 'pop-case');
  });

  test('팝오버(작업 있음 · 끌기 가능)', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&accepts=product,solution,image,case&pop=product&node=fam_G000182628');
    await expect(page.locator('[data-model]')).toHaveCount(7);
    await page.getByRole('button', { name: '추가 QM55C' }).click();
    await page.waitForTimeout(200);
    await shot(page, 'pop-product-task');
    await page.goto('/_dev/shell?task=1&accepts=image&pop=image&q=' + encodeURIComponent('카페 메뉴보드'));
    await expect(page.locator('.wm-tilewrap')).toHaveCount(6);
    const mc = page.locator('.wm-tilewrap', { hasText: '맥도날드 매장 내부' }).first();
    await mc.hover(); // 체크 단추는 호버 · 포커스 때만 보인다
    await mc.getByRole('button', { name: /^선택 맥도날드 매장 내부/ }).click();
    await page.mouse.move(700, 880);
    await page.waitForTimeout(300);
    await shot(page, 'pop-image-task');
  });

  test('제품 상세 시트 3탭', async ({ page }) => {
    await page.goto('/?pop=product&detail=product:LH55QMCEBGCXKR&tab=spec');
    await expect(page.getByRole('dialog', { name: 'QM55C 제품 상세' })).toBeVisible();
    await expect(page.locator('[data-spec-row]').first()).toBeVisible();
    await page.waitForTimeout(300);
    await shot(page, 'sheet-product-spec');
    await page.getByRole('tab', { name: /이미지/ }).click();
    await expect(page.getByLabel('선택한 이미지')).toBeVisible();
    await page.waitForTimeout(300);
    await shot(page, 'sheet-product-images');
    await page.getByRole('tab', { name: /활용 사례/ }).click();
    await expect(page.locator('[data-case-row]')).toHaveCount(3);
    await page.waitForTimeout(300);
    await shot(page, 'sheet-product-cases');
  });

  test('솔루션 상세 시트 3탭', async ({ page }) => {
    await page.goto('/?pop=solution&detail=solution:magicinfo&tab=overview');
    await expect(page.getByRole('dialog', { name: 'MagicINFO 솔루션 상세' })).toBeVisible();
    await expect(page.locator('[data-part]')).toHaveCount(4);
    await page.waitForTimeout(300);
    await shot(page, 'sheet-solution-overview');
    await page.getByRole('tab', { name: /이미지/ }).click();
    await expect(page.locator('[data-image-group]')).toHaveCount(2);
    await page.waitForTimeout(300);
    await shot(page, 'sheet-solution-images');
    await page.getByRole('tab', { name: /활용 사례/ }).click();
    await expect(page.locator('[data-mention]')).toHaveCount(14);
    await page.waitForTimeout(300);
    await shot(page, 'sheet-solution-cases');
  });

  test('스텝바 · 딸깍 · 제품 입력창 · 키트', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&steps=proposal&current=4&oneClick=1&group=proposal');
    await page.getByRole('button', { name: /딸깍/ }).click();
    await expect(page.getByRole('dialog', { name: '딸깍 — 나머지 자동 완성' })).toBeVisible();
    await shot(page, 'stepper-oneclick');
    await page.goto('/_dev/kit');
    const input = page.getByRole('combobox', { name: '제품명 입력' });
    await input.fill('the w');
    await expect(page.getByRole('listbox', { name: '제품 검색 결과' })).toBeVisible();
    await page.getByTestId('product-input').scrollIntoViewIfNeeded();
    await shot(page, 'product-input');
    await page.keyboard.press('Escape');
    await page.screenshot({ path: 'e2e/shell/__screens__/kit.png', fullPage: true });
  });
});
