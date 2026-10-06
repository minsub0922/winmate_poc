/**
 * 기능 격리(proposal-web 요청) — 기능 하나의 index.tsx 가 import 오류(Vite 500)거나 화면을 그리다 오류여도
 * 나머지 기능 · 사이드바 · 홈은 그대로, 그 기능 경로만 한국어 오류 화면. 개발 서버(WM_E2E_DEV=1)에서만 — 모듈 요청을 route 로 바꾼다.
 */
import { expect, test } from '@playwright/test';
import { setupShell } from './fixtures/mock';

test.skip(!process.env.WM_E2E_DEV, '개발 서버(WM_E2E_DEV=1)에서만 — 기능 모듈 요청을 바꿔 깨뜨린다');

const GROUPS = ['고객 요구사항', '전략 수립 Storyboard', '이미지 생성', '공간 조감도 생성', '공간 시나리오 생성', 'Market Intelligence', '경쟁사 분석',
  'Value Proposition', 'Spec 시트 생성', 'B2B 제안서 생성'];

test.describe('기능 격리 (ISO)', () => {
  test('ISO-01 기능 하나 import 오류 → 앱은 뜨고 그 경로만 「이 기능을 불러오지 못했어요」', async ({ page }) => {
    await setupShell(page);
    await page.route(/\/src\/features\/mi\/index\.tsx(\?.*)?$/, (route) => route.fulfill({ status: 500, contentType: 'text/plain', body: 'Failed to resolve import "./nope"' }));
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto('/');
    const nav = page.getByRole('navigation', { name: '작업 내역' });
    await expect(nav).toBeVisible();
    for (const g of GROUPS) await expect(nav.getByRole('link', { name: new RegExp(g) })).toBeVisible();
    await expect(page.locator('[data-greeting]')).toBeVisible();
    await page.goto('/mi');
    const err = page.locator('[data-shell-error]');
    await expect(err).toBeVisible();
    await expect(err).toContainText('이 기능을 불러오지 못했어요');
    await expect(err).toContainText('「Market Intelligence」');
    await expect(page.getByRole('navigation', { name: '현재 위치' })).toContainText('Market Intelligence');
    await err.getByRole('button', { name: '자세한 오류' }).click();
    await expect(err.locator('pre')).toBeVisible();
    await page.screenshot({ path: 'e2e/shell/__screens__/isolation-load-failed.png' });
    await page.goto('/mi/new');
    await expect(page.locator('[data-shell-error]')).toContainText('이 기능을 불러오지 못했어요');
    // 다른 기능은 그대로
    await page.goto('/spec');
    await expect(page.locator('[data-shell-error]')).toHaveCount(0);
    await expect(page.getByRole('navigation', { name: '현재 위치' })).toContainText('Spec 시트 생성');
    expect(errors).toEqual([]);
  });

  test('ISO-02 기능 화면을 그리다 오류 → 셸(사이드바 · 상단바)은 그대로 본문만 「화면을 그리다 문제가 생겼어요」', async ({ page }) => {
    await setupShell(page);
    // spec 기능 모듈을 "목록 화면이 그리다 오류를 던지는" 모듈로 바꾼다(React import 없이 Component 로)
    await page.route(/\/src\/features\/spec\/index\.tsx(\?.*)?$/, (route) => route.fulfill({
      status: 200, contentType: 'application/javascript',
      body: "export default { code: 'SP', key: 'spec', name: 'Spec 시트 생성', order: 9, routes: [{ index: true, Component() { throw new Error('시험용 그리기 오류'); } }] };\n",
    }));
    await page.goto('/spec');
    const err = page.locator('[data-shell-error]');
    await expect(err).toBeVisible();
    await expect(err).toContainText('화면을 그리다 문제가 생겼어요');
    await expect(err).toContainText('「Spec 시트 생성」');
    await expect(page.getByRole('navigation', { name: '작업 내역' })).toBeVisible();
    await expect(page.getByRole('button', { name: '제품 탐색' })).toBeVisible();
    await err.getByRole('button', { name: '자세한 오류' }).click();
    await expect(err.locator('pre')).toContainText('시험용 그리기 오류');
    await page.screenshot({ path: 'e2e/shell/__screens__/isolation-render-error.png' });
    // 홈으로 → 정상
    await err.getByRole('link', { name: '홈으로' }).click();
    await expect(page.locator('[data-greeting]')).toBeVisible();
    await expect(page.locator('[data-shell-error]')).toHaveCount(0);
  });

  test('ISO-03 빈 모듈(export default null) — 그 기능만 오류, 사이드바 이름은 카탈로그 그대로', async ({ page }) => {
    await setupShell(page);
    await page.route(/\/src\/features\/vp\/index\.tsx(\?.*)?$/, (route) => route.fulfill({ status: 200, contentType: 'application/javascript', body: 'export default null;\n' }));
    await page.goto('/vp');
    await expect(page.locator('[data-shell-error]')).toContainText('이 기능을 불러오지 못했어요');
    await expect(page.getByRole('navigation', { name: '작업 내역' }).getByRole('link', { name: /Value Proposition/ })).toBeVisible();
  });
});
