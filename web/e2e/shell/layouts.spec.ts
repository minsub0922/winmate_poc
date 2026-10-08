/**
 * PPT 레이아웃 브라우저 `/layouts`(사이드바 「PPT 레이아웃 브라우저」, 작업 내역 위) — export 카탈로그는 실제 서비스를 쓴다.
 */
import { expect, test } from '@playwright/test';
import { setupShell } from './fixtures/mock';

test.describe('PPT 레이아웃 브라우저 (LB)', () => {
  test.beforeEach(async ({ page }) => {
    await setupShell(page);
    await page.unroute('**/api/export/v1/templates/**'); // 셸 흉내는 썸네일을 404 로 막는다 — 여기서는 실제 카탈로그 · 그림
  });

  test('LB-01 사이드바 버튼이 작업 내역 위 · 누르면 /layouts · 섹션별 카드', async ({ page }) => {
    await page.goto('/');
    const side = page.getByRole('complementary', { name: '사이드바' });
    const btn = side.getByTestId('nav-layouts');
    await expect(btn).toHaveText('PPT 레이아웃 브라우저');
    const btnBox = await btn.boundingBox();
    const overline = await side.getByText('작업 내역', { exact: true }).boundingBox();
    expect(btnBox!.y).toBeLessThan(overline!.y);
    await btn.click();
    await expect(page).toHaveURL(/\/layouts$/);
    await expect(btn).toHaveAttribute('aria-current', 'page');
    await expect(page.getByRole('heading', { name: 'PPT 레이아웃 브라우저' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Market Intelligence' })).toBeVisible();
    expect(await page.locator('.lb-card').count()).toBeGreaterThan(300);
  });

  test('LB-02 검색 — 이름 · 코드(대시 없이도) · 여러 낱말 AND · 없으면 빈 화면', async ({ page }) => {
    await page.goto('/layouts');
    const search = page.getByLabel('레이아웃 검색');
    await search.fill('핵심 수치');
    await expect(page.locator('.lb-card[data-code="MS-A"]')).toBeVisible();
    await expect(page).toHaveURL(/find=/);
    await search.fill('msa');
    await expect(page.locator('.lb-card').first()).toHaveAttribute('data-code', /^MS-A/);
    await search.fill('없는레이아웃이름xyz');
    await expect(page.getByText('맞는 레이아웃이 없어요')).toBeVisible();
    await page.getByRole('button', { name: '조건 지우고 전부 보기' }).click();
    await expect(search).toHaveValue('');
  });

  test('LB-03 섹션 칩 · 제작 중 포함', async ({ page }) => {
    await page.goto('/layouts');
    const ready = await page.locator('.lb-card').count();
    await page.getByRole('group', { name: '섹션' }).getByRole('button', { name: /^Why Samsung/ }).click();
    await expect(page.locator('.lb-group')).toHaveCount(1);
    await page.getByRole('group', { name: '섹션' }).getByRole('button', { name: /^전체/ }).click();
    await page.getByRole('button', { name: '제작 중 포함' }).click();
    await expect(page).toHaveURL(/st=all/);
    expect(await page.locator('.lb-card').count()).toBeGreaterThan(ready);
  });

  test('LB-04 카드 → 상세(원본 보드 · 칸 · 코드 복사) · URL 로 바로 열림', async ({ page }) => {
    await page.goto('/layouts?layout=MS-A');
    const sheet = page.getByTestId('layout-detail');
    await expect(sheet).toBeVisible();
    await expect(sheet.getByRole('img', { name: 'MS-A 원본 보드' })).toBeVisible();
    await expect(sheet.getByText('칸(slots)')).toBeVisible();
    await expect(sheet.getByText('title', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: '와이어프레임' }).click();
    await expect(sheet.getByRole('img', { name: 'MS-A 와이어프레임' })).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(sheet).toHaveCount(0);
    await expect(page).not.toHaveURL(/layout=/);
  });
});
