/**
 * 00-shell §8.9 끌어서 추가(D). 개발 화면 `/_dev/shell` 의 DropZone 이 놓는 곳이다(onDrop 은 호출 기록에 남는다).
 * HTML5 끌기는 Playwright 마우스(누른 채 이동)로 낸다 — 크로미움은 끌기를 가로채 dragover · drop 을 보낸다.
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { devLog, setupShell } from './fixtures/mock';

const css = (loc: Locator, prop: string) => loc.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
const ghost = (page: Page) => page.getByTestId('drag-ghost');
const dropZone = (page: Page) => page.getByLabel('끌어 놓는 영역');

/** 원천의 (dx, 가운데)를 누르고 조금씩 끌어 (tx, ty) 까지 옮긴다 */
async function dragTo(page: Page, src: Locator, tx: number, ty: number, dx = 120) {
  const b = (await src.boundingBox())!;
  const x = b.x + Math.min(dx, b.width / 2);
  const y = b.y + b.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 8, y + 4, { steps: 2 });
  await page.mouse.move(tx, ty, { steps: 8 });
}
/** 드롭 영역 왼쪽(팝오버에 덮이지 않는 쪽) 한가운데 */
async function zonePoint(page: Page) {
  const z = (await dropZone(page).boundingBox())!;
  return { x: z.x + 60, y: z.y + z.height / 2 };
}

test.beforeEach(async ({ page }) => { await setupShell(page); });

test.describe('끌어서 추가 (D)', () => {
  test('D-01 · D-02 제품 행 끌기 → 팝오버 흐림 · 행 점선 · 고스트 → 놓기 → onDrop 한 번 · ✓ 추가됨', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&accepts=product&pop=product&node=fam_G000182628');
    const pop = page.getByRole('dialog', { name: '제품 탐색' });
    const row = pop.locator('[data-model="LH65QMCEBGCXKR"]');
    await expect(row).toHaveAttribute('draggable', 'true');
    await expect(dropZone(page)).toHaveAttribute('data-drop-state', 'idle');
    const zp = await zonePoint(page);

    await dragTo(page, row, zp.x + 40, zp.y + 120);
    // 끄는 중: 팝오버 0.35 · 클릭 통과, 행 0.45 · 점선 윤곽, 고스트(모델 이름)
    await expect.poll(() => css(pop, 'opacity')).toBe('0.35');
    expect(await css(pop, 'pointer-events')).toBe('none');
    await expect.poll(() => css(row, 'opacity')).toBe('0.45');
    expect(await css(row, 'outline-style')).toBe('dashed');
    await expect(ghost(page)).toBeVisible();
    await expect(ghost(page)).toHaveAttribute('data-ref', 'kb:model:mdl_LH65QMCEBGCXKR');
    await expect(ghost(page).locator('.wm-ghost__label')).toHaveText('QM65C');
    await expect(ghost(page).locator('.wm-ghost__sub')).toContainText('제품 · 단독형 UHD M 시리즈');
    // 고스트는 커서 곁에 있다
    const gb = (await ghost(page).boundingBox())!;
    expect(Math.abs(gb.x + gb.width - (zp.x + 40))).toBeLessThan(60);
    expect(Math.abs(gb.y - (zp.y + 120))).toBeLessThan(60);
    // 받는 곳은 h76 강조 + 「QM65C」
    await expect(dropZone(page)).toHaveAttribute('data-drop-state', /dragging|over/);
    await expect(dropZone(page)).toContainText('여기에 놓아 「QM65C」 추가');

    await page.mouse.move(zp.x, zp.y, { steps: 6 });
    await expect(dropZone(page)).toHaveAttribute('data-drop-state', 'over');
    await page.screenshot({ path: 'e2e/shell/__screens__/dnd-product.png' });
    await page.mouse.up();

    await expect(dropZone(page)).toContainText('「QM65C」 추가됨');
    const log = (await devLog(page)).filter((e) => e.kind === 'onDrop');
    expect(log).toHaveLength(1);
    expect(log[0].payload).toMatchObject({ type: 'product', ref: 'kb:model:mdl_LH65QMCEBGCXKR', label: 'QM65C' });
    await expect(ghost(page)).toHaveCount(0);
    await expect.poll(() => css(pop, 'opacity')).toBe('1');
    await expect(row.getByRole('button', { name: /QM65C/ })).toHaveText(/✓ 추가됨/);
    await expect(row).not.toHaveAttribute('draggable', 'true'); // 추가된 행은 더 끌 수 없다
    await expect(page.getByTestId('dev-added')).toContainText('kb:model:mdl_LH65QMCEBGCXKR');

    // 실행 취소 → onUndo
    await dropZone(page).getByRole('button', { name: '실행 취소' }).click();
    await expect.poll(async () => (await devLog(page)).filter((e) => e.kind === 'undo').length).toBe(1);
    await expect(dropZone(page)).toHaveAttribute('data-drop-state', 'idle');
  });

  test('D-03 끄는 중 Esc → onDrop 없음 · 팝오버 불투명도 1', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&accepts=product&pop=product&node=fam_G000182628');
    const pop = page.getByRole('dialog', { name: '제품 탐색' });
    const row = pop.locator('[data-model="LH65QMCEBGCXKR"]');
    const zp = await zonePoint(page);
    await dragTo(page, row, zp.x, zp.y);
    await expect(ghost(page)).toBeVisible();
    await expect.poll(() => css(pop, 'opacity')).toBe('0.35');
    await page.keyboard.press('Escape');
    await expect(ghost(page)).toHaveCount(0);
    await expect.poll(() => css(pop, 'opacity')).toBe('1');
    await page.mouse.up();
    await page.waitForTimeout(200);
    expect((await devLog(page)).filter((e) => e.kind === 'onDrop')).toHaveLength(0);
    await expect(pop).toBeVisible(); // Esc 는 끌기만 취소하고 팝오버는 그대로
    await expect(row.getByRole('button', { name: /QM65C/ })).not.toHaveText(/추가됨/);
  });

  test('D-04 accepts 에 image 없음 → 이미지 타일 손잡이 없음 · 있으면 있음', async ({ page }) => {
    const q = encodeURIComponent('카페 메뉴보드');
    await page.goto(`/_dev/shell?task=1&accepts=product&pop=image&q=${q}`);
    const pop = page.getByRole('dialog', { name: '이미지 검색' });
    await expect(pop.locator('.wm-tilewrap')).toHaveCount(6);
    await expect(pop.locator('.wm-tile__grip')).toHaveCount(0);
    await expect(pop.locator('.wm-tilewrap[draggable="true"]')).toHaveCount(0);
    await page.goto(`/_dev/shell?task=1&accepts=image&pop=image&q=${q}`);
    await expect(pop.locator('.wm-tilewrap')).toHaveCount(6);
    await expect(pop.locator('.wm-tile__grip')).toHaveCount(6);
    await expect(pop.locator('.wm-tilewrap[draggable="true"]')).toHaveCount(6);
  });

  test('D-04b 이미지 타일 · 사례 카드 · 솔루션 행도 같은 데이터로 끌린다', async ({ page }) => {
    await page.goto(`/_dev/shell?task=1&accepts=image,case,solution&pop=image&q=${encodeURIComponent('카페 메뉴보드')}`);
    const zp = await zonePoint(page);
    const tile = page.locator('.wm-tilewrap', { hasText: '맥도날드 매장 내부' }).first();
    await dragTo(page, tile, zp.x, zp.y, 60);
    await expect(ghost(page)).toHaveAttribute('data-ref', 'kb:image:img_0b58832faefa0ff4');
    await page.mouse.up();
    await expect(dropZone(page)).toContainText('추가됨');

    await page.goto(`/_dev/shell?task=1&accepts=image,case,solution&pop=solution`);
    const sol = page.locator('[data-solution="magicinfo"]');
    await dragTo(page, sol, (await zonePoint(page)).x, (await zonePoint(page)).y, 80);
    await expect(ghost(page)).toHaveAttribute('data-ref', 'kb:solution:magicinfo');
    await page.mouse.up();

    await page.goto(`/_dev/shell?task=1&accepts=image,case,solution&pop=case&q=${encodeURIComponent('프랜차이즈 메뉴보드')}`);
    const card = page.locator('[data-case-card]').first();
    await expect(card).toBeVisible();
    await dragTo(page, card, (await zonePoint(page)).x, (await zonePoint(page)).y, 300);
    await expect(ghost(page)).toHaveAttribute('data-ref', /^kb:case:dep_/);
    await page.mouse.up();
    const drops = (await devLog(page)).filter((e) => e.kind === 'onDrop');
    expect(drops.length).toBeGreaterThanOrEqual(1);
    expect((drops.at(-1)!.payload as { type: string }).type).toBe('case');
  });

  test('D-05 MI 작업을 받는 화면 → 사이드바 MI 항목 끌기 · 고스트 `사이드바 · Market Intelligence` / 안 받으면 안 끌림', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&accepts=work_item&work=MI&group=mi');
    const mi = page.locator('[data-group="mi"] .sh-item').first();
    await expect(mi).toBeVisible();
    await expect(mi).toHaveAttribute('draggable', 'true');
    await expect(dropZone(page)).toContainText('MI 작업 (사이드바)');

    const zp = await zonePoint(page);
    await dragTo(page, mi, zp.x, zp.y, 60);
    await expect(ghost(page)).toBeVisible();
    await expect(ghost(page).locator('.wm-ghost__sub')).toHaveText('사이드바 · Market Intelligence');
    await page.screenshot({ path: 'e2e/shell/__screens__/dnd-sidebar.png' });
    expect((await ghost(page).boundingBox())!.width).toBeGreaterThan(280); // 사이드바 작업 고스트는 290
    await page.mouse.up();
    const drop = (await devLog(page)).filter((e) => e.kind === 'onDrop');
    expect(drop).toHaveLength(1);
    expect(drop[0].payload).toMatchObject({ type: 'work_item', feature: 'MI' });
    expect((drop[0].payload as { ref: string }).ref).toMatch(/^ws:item:/);

    // 같은 화면이라도 다른 기능(VP) 항목은 끌리지 않는다(링크 기본 끌기도 끔)
    await page.locator('[data-group="vp"]').getByRole('button', { name: 'Value Proposition 펼치기' }).click();
    await expect(page.locator('[data-group="vp"] .sh-item').first()).toBeVisible();
    await expect(page.locator('[data-group="vp"] .sh-item[draggable="true"]')).toHaveCount(0);
    await expect(page.locator('[data-group="vp"] .sh-item').first()).toHaveAttribute('draggable', 'false');

    // 받지 않는 화면
    await page.goto('/_dev/shell?task=1&accepts=product&group=mi');
    await expect(page.locator('[data-group="mi"] .sh-item').first()).toBeVisible();
    await expect(page.locator('.sh-item[draggable="true"]')).toHaveCount(0);
  });
});
