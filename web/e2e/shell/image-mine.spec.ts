/**
 * 이미지 검색 「내 생성 이미지」 탭 — image 서비스 API 를 쓰는지(docs/requests/image.md 첫 항목):
 * `GET /api/image/v1/images?owner=me&q=&limit=24` · 정보 패널 `GET /api/image/v1/images/{id}/info` 행 · 참조 `img:image:<id>`.
 */
import { expect, test } from '@playwright/test';
import { devLog, setupShell } from './fixtures/mock';

const GEN = {
  id: 'img_GEN1', title: '메뉴보드 시안 1', width: 1920, height: 1080, format: 'PNG', bytes: 740595, created_at: '2026-10-06T10:08:17.715Z',
  file_id: 'file_x', thumb_url: '/api/kb/v1/_fixture/img/gen1.svg', kind: 'space', route: '/image/w/imw_1/result?image=img_GEN1',
};
const INFO = {
  image_id: 'img_GEN1', version_id: 'imv_1', title: '메뉴보드 시안 1',
  rows: [
    { k: '출처 페이지', v: 'Winmate 이미지 작업', href: '/image/w/imw_1/result?image=img_GEN1' },
    { k: '원본', v: '1024×576 · PNG · 생성 2026-10-06', href: null },
    { k: '저장본', v: '1920×1080 · 업스케일', href: null },
    { k: '사용 조건', v: '“AI 생성 이미지” 표기 권장 · 대외 사용 범위 확인 필요', href: null },
    { k: '사용 이력', v: 'Winmate 제안서 1건', href: null },
  ],
};

test('IMG-MINE-01 내 생성 이미지 탭 — image 목록 · 정보 행 · img:image 참조로 추가', async ({ page }) => {
  await setupShell(page);
  const listCalls: string[] = [];
  await page.route('**/api/image/v1/images**', (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/image/v1/images') {
      listCalls.push(url.search);
      return route.fulfill({ json: { items: [GEN], total: 1, next_cursor: null } });
    }
    if (url.pathname === `/api/image/v1/images/${GEN.id}/info`) return route.fulfill({ json: INFO });
    return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: '없음', details: {} } } });
  });
  await page.goto(`/_dev/shell?task=1&accepts=image&pop=image&q=${encodeURIComponent('메뉴보드')}`);
  const pop = page.getByRole('dialog', { name: '이미지 검색' });
  const tabs = pop.getByRole('tablist', { name: '이미지 출처' });
  await expect(tabs.getByRole('tab', { name: /내 생성 이미지/ })).toContainText('1');
  expect(listCalls.some((s) => s.includes('owner=me') && s.includes('q=%EB%A9%94%EB%89%B4%EB%B3%B4%EB%93%9C') && s.includes('limit=24'))).toBe(true);
  await tabs.getByRole('tab', { name: /내 생성 이미지/ }).click();
  const tile = pop.locator('.wm-tile').first();
  await expect(tile).toHaveAttribute('aria-label', '메뉴보드 시안 1 — 생성 이미지, 출처 Winmate');
  await tile.click();
  const info = pop.getByRole('complementary', { name: '이미지 정보' });
  await expect(info.locator('[data-key="사용 이력"]')).toContainText('Winmate 제안서 1건');
  await expect(info.locator('[data-key="저장본"]')).toContainText('1920×1080 · 업스케일');
  await expect(info.locator('[data-key="출처 페이지"] a')).toHaveAttribute('href', '/image/w/imw_1/result?image=img_GEN1');
  // 고르고 현재 작업에 추가 → 참조 img:image:<id>
  const wrap = pop.locator('.wm-tilewrap').first();
  await wrap.hover();
  await wrap.locator('.wm-tile__check').click();
  await pop.getByRole('button', { name: /현재 작업에 추가/ }).click();
  await expect.poll(async () => (await devLog(page)).find((e) => e.kind === 'onAdd')).toMatchObject({ type: 'image', refs: ['img:image:img_GEN1'] });
});
