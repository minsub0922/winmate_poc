/**
 * 00-shell §8.12 제품 입력창(PI) · §8.13 스텝바(ST) · §8.15 X-03 · X-04 + 키트 부품(Thumb · 확인창 · 토스트).
 * 제품 입력창은 `/_dev/kit`, 스텝바는 `/_dev/shell?steps=…`.
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { devLog, setupShell } from './fixtures/mock';

const css = (loc: Locator, prop: string) => loc.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
const pi = (page: Page) => page.getByTestId('product-input');
const input = (page: Page) => pi(page).getByRole('combobox');
const panel = (page: Page) => page.getByRole('listbox', { name: '제품 검색 결과' });
const bubbles = (page: Page) => pi(page).locator('[data-bubble]');

test.beforeEach(async ({ page }) => { await setupShell(page); });

test.describe('제품 입력창 (PI)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/_dev/kit');
    await expect(input(page)).toBeVisible();
  });

  test('PI-01 `the w` → 패널이 입력창 위 · 머리 글 · 5행 이하 · 실내용 The Wall IWC · 맞은 글자 #1428a0', async ({ page }) => {
    await input(page).fill('the w');
    const p = panel(page);
    await expect(p).toBeVisible();
    await expect(p.getByRole('option').first()).toBeVisible();
    const pb = (await p.boundingBox())!;
    const ib = (await pi(page).locator('.wm-tokens__box').boundingBox())!;
    expect(pb.y + pb.height).toBeLessThan(ib.y);
    await expect(p.locator('.wm-results__head').first()).toHaveText('"the w" 검색 결과 · 방향키로 이동, Enter로 추가');
    const n = await p.getByRole('option').count();
    expect(n).toBeGreaterThan(0);
    expect(n).toBeLessThanOrEqual(5);
    const iwc = p.getByRole('option').filter({ has: page.locator('.wm-result__name', { hasText: /^실내용 The Wall IWC$/ }) });
    await expect(iwc).toBeVisible();
    const mark = iwc.locator('mark').first();
    await expect(mark).toHaveText(/the w/i);
    expect(await css(mark, 'color')).toBe('rgb(20, 40, 160)');
    await expect(input(page)).toHaveAttribute('aria-expanded', 'true');
  });

  test('PI-02 ↓ 후 Enter → 활성 행(#eaeefb · 추가 ↵)이 파란 버블 · 입력창 비고 포커스 유지', async ({ page }) => {
    await input(page).fill('the w');
    const opts = panel(page).getByRole('option');
    await expect(opts.nth(1)).toBeVisible();
    await expect(opts.nth(0)).toHaveAttribute('aria-selected', 'true');
    await input(page).press('ArrowDown');
    const active = opts.nth(1);
    await expect(active).toHaveAttribute('aria-selected', 'true');
    expect(await css(active, 'background-color')).toBe('rgb(234, 238, 251)');
    await expect(active.locator('.wm-result__cta')).toHaveText('추가 ↵');
    const name = (await active.locator('.wm-result__name').textContent())!.trim();
    await input(page).press('Enter');
    await expect(bubbles(page)).toHaveCount(1);
    await expect(bubbles(page).first()).toHaveAttribute('data-bubble', 'matched');
    await expect(bubbles(page).first()).toContainText(name);
    await expect(input(page)).toHaveValue('');
    await expect(input(page)).toBeFocused();
    await expect(panel(page)).toHaveCount(0);
    await expect(page.getByTestId('product-input-value')).toContainText('"ref":"kb:');
  });

  test('PI-03 `"the w" 그대로 추가` → 점선 버블', async ({ page }) => {
    await input(page).fill('the w');
    await panel(page).getByRole('button', { name: '"the w" 그대로 추가' }).click();
    await expect(bubbles(page)).toHaveCount(1);
    await expect(bubbles(page).first()).toHaveAttribute('data-bubble', 'custom');
    await expect(bubbles(page).first()).toHaveText('the w');
    expect(await css(bubbles(page).first(), 'border-top-style')).toBe('dashed');
    await expect(page.getByTestId('product-input-value')).toContainText('"kind":"custom"');
  });

  test('PI-04 · PI-05 제거 버튼 · 빈 입력 Backspace', async ({ page }) => {
    for (const t of ['the w', 'qm55']) {
      await input(page).fill(t);
      await expect(panel(page).getByRole('option').first()).toBeVisible();
      await input(page).press('Enter');
    }
    await expect(bubbles(page)).toHaveCount(2);
    const first = (await bubbles(page).first().textContent())!.trim();
    await pi(page).getByRole('button', { name: `${first} 제거` }).click();
    await expect(bubbles(page)).toHaveCount(1);
    await input(page).focus();
    await input(page).press('Backspace');
    await expect(bubbles(page)).toHaveCount(0);
  });

  test('PI-06 Esc → 결과 패널 닫힘(입력은 그대로)', async ({ page }) => {
    await input(page).fill('the w');
    await expect(panel(page)).toBeVisible();
    await input(page).press('Escape');
    await expect(panel(page)).toHaveCount(0);
    await expect(input(page)).toHaveValue('the w');
    await expect(input(page)).toHaveAttribute('aria-expanded', 'false');
  });

  test('PI-07 같은 제품을 다시 고르면 버블이 늘지 않는다 · `이미 추가됨`', async ({ page }) => {
    await input(page).fill('the w');
    await expect(panel(page).getByRole('option').first()).toBeVisible();
    await input(page).press('Enter');
    await expect(bubbles(page)).toHaveCount(1);
    await input(page).fill('the w');
    await expect(panel(page).getByRole('option').first().locator('.wm-result__cta')).toHaveText('이미 추가됨');
    await input(page).press('Enter');
    await expect(bubbles(page)).toHaveCount(1);
    // 직접 입력도 같은 글이면 한 번만
    for (let i = 0; i < 2; i++) {
      await input(page).fill('없는 제품 X');
      await panel(page).getByRole('button', { name: '"없는 제품 X" 그대로 추가' }).click();
    }
    await expect(bubbles(page)).toHaveCount(2);
  });

  test('PI-x 결과가 오기 전에 Enter → 결과가 오면 첫 행을 넣는다', async ({ page }) => {
    await input(page).fill('the w');
    await input(page).press('Enter'); // 디바운스(150ms) 전
    await expect(bubbles(page)).toHaveCount(1);
    await expect(bubbles(page).first()).toHaveAttribute('data-bubble', 'matched');
  });
});

test.describe('스텝바 (ST)', () => {
  const circle = (page: Page, k: number) => page.locator(`.sh-steps [data-step="${k}"] .sh-step__circle`);
  const line = (page: Page, k: number) => page.locator(`.sh-steps [data-step="${k}"] .sh-step__line`);

  test('ST-01 3단계 current=2 — 원 · 숫자 · 선 폭 56 · 선 색', async ({ page }) => {
    await page.goto('/_dev/shell?steps=고객,구성,생성&current=2');
    await expect(circle(page, 1)).toHaveAttribute('data-state', 'done');
    expect(await css(circle(page, 1), 'background-color')).toBe('rgb(20, 40, 160)');
    await expect(circle(page, 1).locator('svg')).toHaveCount(1);
    await expect(circle(page, 2)).toHaveAttribute('data-state', 'active');
    await expect(circle(page, 2)).toHaveText('2');
    expect(await css(circle(page, 2), 'border-top-color')).toBe('rgb(20, 40, 160)');
    await expect(circle(page, 3)).toHaveAttribute('data-state', 'todo');
    expect(await css(circle(page, 3), 'border-top-color')).toBe('rgb(213, 217, 224)');
    expect((await line(page, 1).boundingBox())!.width).toBe(56);
    expect(await css(line(page, 1), 'background-color')).toBe('rgb(20, 40, 160)');
    expect(await css(line(page, 2), 'background-color')).toBe('rgb(213, 217, 224)');
    await expect(page.locator('.sh-steps [aria-current="step"]')).toHaveAttribute('data-step', '2');
  });

  test('ST-02 6단계 — 이름 12.5px · 선 28 · 여백 8', async ({ page }) => {
    await page.goto('/_dev/shell?steps=proposal&current=2');
    await expect(page.locator('.sh-steps > li')).toHaveCount(6);
    const label = page.locator('.sh-steps [data-step="1"] .sh-step > span').nth(1);
    expect(await css(label, 'font-size')).toBe('12.5px');
    expect((await line(page, 1).boundingBox())!.width).toBe(28);
    expect(await css(line(page, 1), 'margin-left')).toBe('8px');
    expect(await css(line(page, 1), 'margin-right')).toBe('8px');
  });

  test('ST-03 complete → 모든 원이 체크', async ({ page }) => {
    await page.goto('/_dev/shell?steps=고객,구성,생성&current=2&complete=1');
    for (let k = 1; k <= 3; k++) await expect(circle(page, k)).toHaveAttribute('data-state', 'done');
    await expect(page.locator('.sh-steps [aria-current="step"]')).toHaveCount(0);
  });

  test('ST-04 current=6 · autoFrom=4 · complete → 4–6 검은 번개 · 딸깍 없음', async ({ page }) => {
    await page.goto('/_dev/shell?steps=proposal&current=6&autoFrom=4&complete=1&oneClick=1');
    for (let k = 1; k <= 3; k++) await expect(circle(page, k)).toHaveAttribute('data-state', 'done');
    for (let k = 4; k <= 6; k++) {
      await expect(circle(page, k)).toHaveAttribute('data-state', 'auto');
      expect(await css(circle(page, k), 'background-color')).toBe('rgb(18, 20, 23)');
    }
    await expect(page.getByRole('button', { name: /딸깍/ })).toHaveCount(0);
  });

  test('ST-05 제안서 current=4 · 딸깍 → 대화상자(확정 3 · 행 3 · 남은 3단계 · 체크 2) · 취소 · 완성하기 한 번', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&steps=proposal&current=4&oneClick=1&group=proposal');
    const btn = page.getByRole('button', { name: /딸깍/ });
    await expect(btn).toHaveAttribute('title', '남은 단계를 AI가 추론해 최종 제안서를 바로 만듭니다');
    const sb = (await page.locator('.sh-stepper').boundingBox())!;
    const bb = (await btn.boundingBox())!;
    expect(sb.x + sb.width - (bb.x + bb.width)).toBeLessThan(40); // 오른쪽 끝
    await btn.click();
    const d = page.getByRole('dialog', { name: '딸깍 — 나머지 자동 완성' });
    await expect(d).toBeVisible();
    await expect(d.locator('[data-confirmed] .wm-checkchip')).toHaveText(['고객 · 프로젝트', '제안서 유형', '시트 구성']);
    const rows = d.locator('[data-plan-row]');
    await expect(rows).toHaveCount(3);
    await expect(rows.nth(0)).toContainText('섹션 작성');
    await expect(rows.nth(0)).toContainText('입력한 내용까지 반영하고 나머지 추론');
    await expect(rows.nth(1)).toContainText('추론해 자동 완성');
    await expect(rows.nth(2)).toContainText('추론해 자동 완성');
    await expect(d.locator('[data-summary]')).toHaveText('남은 3단계');
    const boxes = d.getByRole('checkbox');
    await expect(boxes).toHaveCount(2);
    for (let i = 0; i < 2; i++) await expect(boxes.nth(i)).toBeChecked();
    await d.getByRole('button', { name: '취소' }).click();
    await expect(d).toHaveCount(0);
    expect((await devLog(page)).filter((e) => e.kind === 'oneClick')).toHaveLength(0);
    await btn.click();
    await d.getByRole('button', { name: '딸깍, 완성하기' }).click();
    await expect(d).toHaveCount(0);
    const runs = (await devLog(page)).filter((e) => e.kind === 'oneClick');
    expect(runs).toEqual([{ kind: 'oneClick', markInferred: true, collectReview: true }]);
  });

  test('ST-05b 체크를 끄면 그 값으로 · Esc 로 닫힘', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&steps=proposal&current=4&oneClick=1&open=1');
    const d = page.getByRole('dialog', { name: '딸깍 — 나머지 자동 완성' });
    await expect(d).toBeVisible();
    await d.getByRole('checkbox').nth(0).uncheck();
    await d.getByRole('button', { name: '딸깍, 완성하기' }).click();
    expect((await devLog(page)).filter((e) => e.kind === 'oneClick')).toEqual([{ kind: 'oneClick', markInferred: false, collectReview: true }]);
    await page.getByRole('button', { name: /딸깍/ }).click();
    await expect(d).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(d).toHaveCount(0);
  });

  test('ST-06 oneClick + complete → 딸깍 없음 · 단계 가운데', async ({ page }) => {
    await page.goto('/_dev/shell?steps=proposal&current=6&complete=1&oneClick=1');
    await expect(page.getByRole('button', { name: /딸깍/ })).toHaveCount(0);
    const sb = (await page.locator('.sh-stepper').boundingBox())!;
    const ob = (await page.locator('.sh-steps').boundingBox())!;
    expect(Math.abs((ob.x + ob.width / 2) - (sb.x + sb.width / 2))).toBeLessThan(2);
  });
});

test.describe('접근성 (X-03 · X-04)', () => {
  test('X-03 비활성 버튼은 모두 title 로 이유를 보인다', async ({ page }) => {
    const urls = [
      '/?pop=product&node=fam_G000182628', '/?pop=solution', `/?pop=image&q=${encodeURIComponent('카페 메뉴보드')}`, `/?pop=case&q=${encodeURIComponent('프랜차이즈 메뉴보드')}`,
      '/?detail=product:LH55QMCEBGCXKR&tab=images', '/?detail=solution:magicinfo&tab=images', '/?detail=solution:knox_capture',
      '/_dev/shell?task=1&accepts=product&pop=image&q=x', '/_dev/shell?task=1&accepts=product,image&pop=product&node=fam_G000182628',
    ];
    for (const u of urls) {
      await page.goto(u);
      await expect(page.getByRole('dialog').first()).toBeVisible();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(400);
      const bad = await page.locator('button:disabled').evaluateAll((els) => els
        .filter((e) => (e as HTMLElement).offsetParent !== null && !(e.getAttribute('title') ?? '').trim())
        .map((e) => e.outerHTML.slice(0, 160)));
      expect(bad, u).toEqual([]);
    }
  });

  test('X-04 끌기 없이 키보드만으로 추가(+ 추가 → 현재 작업에 추가)', async ({ page }) => {
    await page.goto('/_dev/shell?task=1&accepts=product&pop=product&node=fam_G000182628');
    const pop = page.getByRole('dialog', { name: '제품 탐색' });
    await expect(pop.locator('[data-model]')).toHaveCount(7);
    const add = pop.getByRole('button', { name: '추가 QM65C' });
    await add.focus();
    await page.keyboard.press('Enter');
    await expect(pop.getByRole('button', { name: '선택 해제 QM65C' })).toBeVisible();
    const footer = pop.getByRole('button', { name: '현재 작업에 추가' });
    await expect(footer).toBeEnabled();
    await footer.focus();
    await page.keyboard.press('Enter');
    await expect.poll(async () => (await devLog(page)).filter((e) => e.kind === 'onAdd').map((e) => e.refs)).toEqual([['kb:model:mdl_LH65QMCEBGCXKR']]);
    await expect(pop.locator('[data-model="LH65QMCEBGCXKR"]')).toContainText('✓ 추가됨');
    // Space 로도 고른다
    await pop.getByRole('button', { name: '추가 QM75C' }).focus();
    await page.keyboard.press('Space');
    await expect(pop.getByRole('button', { name: '선택 해제 QM75C' })).toBeVisible();
  });
});

test.describe('키트 부품', () => {
  test('Thumb — 그림 종류마다 SVG · 모르는 종류는 table · code 는 export PNG 없으면 그림', async ({ page }) => {
    await page.goto('/_dev/kit');
    const thumbs = page.getByTestId('thumbs').locator('.wm-thumb');
    await expect(thumbs.first()).toBeVisible(); // 키트 화면은 지연 로딩
    expect(await thumbs.count()).toBeGreaterThan(60);
    const empty = await thumbs.evaluateAll((els) => els.filter((e) => !e.querySelector('svg *, img')).length);
    expect(empty).toBe(0);
    await expect(page.locator('.wm-thumb[data-kind="unknown-kind"] svg')).toHaveCount(1);
    const coded = page.getByTestId('thumb-code').locator('.wm-thumb');
    await expect(coded).toHaveAttribute('aria-label', 'MGI-S-RT 표지');
    await expect(coded.locator('svg')).toHaveCount(1); // 목업 export 는 404 → 그림
    await expect(coded.locator('img')).toHaveCount(0);
  });

  test('ConfirmDialog(useConfirm) · toast', async ({ page }) => {
    await page.goto('/_dev/kit');
    await page.getByRole('button', { name: '확인창 열기' }).click();
    const d = page.getByRole('dialog', { name: '이 작업을 지울까요?' });
    await expect(d).toBeVisible();
    await expect(d).toContainText('지운 작업은 되돌릴 수 없어요.');
    await page.keyboard.press('Escape');
    await expect(d).toHaveCount(0);
    await expect(page.getByTestId('confirm-answer')).toHaveText('false');
    await page.getByRole('button', { name: '확인창 열기' }).click();
    await d.getByRole('button', { name: '지우기' }).click();
    await expect(page.getByTestId('confirm-answer')).toHaveText('true');

    await page.getByRole('button', { name: '토스트' }).click();
    const t = page.getByRole('status').filter({ hasText: '작업을 저장했어요' });
    await expect(t).toBeVisible();
    await t.getByRole('button', { name: '열기' }).click();
    await expect(t).toHaveCount(0);
    await expect(page.getByTestId('confirm-answer')).toHaveText('toast-action');
  });
});
