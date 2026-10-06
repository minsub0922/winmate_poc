/**
 * 00-shell §8.7 이미지 검색(I) · §8.8 유관 사례 검색(C) · §8.15 X-02 · X-05.
 */
import { expect, test, type Page } from '@playwright/test';
import { devLog, setupShell } from './fixtures/mock';

const css = (loc: import('@playwright/test').Locator, prop: string) => loc.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
const Q_IMG = encodeURIComponent('카페 메뉴보드');
const Q_CASE = encodeURIComponent('프랜차이즈 메뉴보드');
const imgPop = (page: Page) => page.getByRole('dialog', { name: '이미지 검색' });
const casePop = (page: Page) => page.getByRole('dialog', { name: '유관 사례 검색' });
/** 타일 본 버튼(포커스) — aria-label `{제목} — {kind} 이미지, 출처 …` */
const tiles = (page: Page) => imgPop(page).locator('.wm-tile');

test.beforeEach(async ({ page }) => { await setupShell(page); });

test.describe('이미지 검색 (I)', () => {
  test('I-01 · X-02 탭 순서 · 숫자 · 전체 = 나머지 합', async ({ page }) => {
    await page.goto(`/?pop=image&q=${Q_IMG}`);
    const tl = imgPop(page).getByRole('tablist', { name: '이미지 출처' });
    const tabs = tl.getByRole('tab');
    await expect(tabs).toHaveCount(5);
    await expect(tiles(page)).toHaveCount(6);
    await expect(tabs).toHaveText(['전체6', '제품 이미지1', '유관 사례 이미지5', '내 생성 이미지0', '사내 자산0']);
    const nums = (await tabs.locator('.wm-tab__n').allTextContents()).map(Number);
    expect(nums[0]).toBe(nums[1] + nums[2] + nums[3] + nums[4]);
    await expect(tabs.first()).toHaveAttribute('aria-selected', 'true');
  });

  test('I-02 · I-03 타일 메타 · aria-label · 첫 타일 포커스 · 패널 키 순서', async ({ page }) => {
    await page.goto(`/?pop=image&q=${Q_IMG}`);
    const t = tiles(page);
    await expect(t).toHaveCount(6);
    const metas = await imgPop(page).locator('.wm-tile__meta').allTextContents();
    for (const m of metas) expect(m).toMatch(/^(제품|도입사례|솔루션|업종) · \d+×\d+ · samsung\.com$/);
    for (let i = 0; i < 6; i++) expect(await t.nth(i).getAttribute('aria-label')).toMatch(/^.+ — (제품|도입사례|솔루션|업종) 이미지, 출처 samsung\.com$/);
    await expect(t.first()).toHaveAttribute('aria-pressed', 'true');
    for (let i = 1; i < 6; i++) await expect(t.nth(i)).toHaveAttribute('aria-pressed', 'false');
    expect(await css(t.first(), 'border-top-color')).toBe('rgb(20, 40, 160)');
    expect(await css(t.first(), 'border-top-width')).toBe('2px');
    const aside = page.locator('aside[aria-label="이미지 정보"]');
    await expect(aside.locator('.wm-meta__k')).toHaveText(['출처 페이지', '원본 파일', '원본', '저장본', '수집', '사용 조건', '사용 이력']);
  });

  test('I-04 · I-05 · I-10 사용 조건(도입사례/제품) · 다른 타일 포커스 · 맥도날드 메타', async ({ page }) => {
    await page.goto(`/?pop=image&q=${Q_IMG}`);
    const aside = page.locator('aside[aria-label="이미지 정보"]');
    const row = (k: string) => aside.locator(`[data-key="${k}"] .wm-meta__v`);
    // 첫 장 = 맥도날드 매장 내부(img_0b58832faefa0ff4, image_sources mcd3_inside)
    await expect(aside).toContainText('맥도날드 매장 내부 메뉴보드');
    await expect(row('사용 조건')).toHaveText('“도입사례 사진” 표기 필수 · 대외 사용 범위 확인 필요');
    await expect(row('원본')).toHaveText('1340 × 820 · JPG · 368 KB · 출처 게시 2020-11-12');
    await expect(row('저장본')).toHaveText('1100 × 673 · JPG · 116 KB · 긴 변 축소');
    await expect(row('원본 파일')).toHaveText('images.samsung.com/kdp/editor/board/202011/3dbd0331….jpg ↗');
    await expect(row('원본 파일')).toHaveAttribute('href', 'https://images.samsung.com/kdp/editor/board/202011/3dbd0331-2a8e-4e5c-ae3a-de796dd5d93d.jpg');
    await expect(row('출처 페이지')).toHaveAttribute('href', 'https://www.samsung.com/sec/business/insights/case-study/reference-MCDONALDSsamsong/');
    await expect(row('수집')).toHaveText('2026-10-04 · 공식 페이지에서 수집');
    await expect(row('사용 이력')).toHaveText('Winmate 제안서 0건');
    // 제품 이미지로 포커스 이동
    const product = tiles(page).filter({ has: page.locator('.wm-badge--product') });
    await product.click();
    await expect(product).toHaveAttribute('aria-pressed', 'true');
    await expect(tiles(page).first()).toHaveAttribute('aria-pressed', 'false');
    await expect(aside).toContainText('QM55C 우측 45도');
    await expect(row('사용 조건')).toHaveText('대외 사용 범위 확인 필요');
  });

  test('I-06 끌기 불가 → 토글(켜짐) / 끌기 가능 → `끌어서 바로 추가`', async ({ page }) => {
    await page.goto(`/?pop=image&q=${Q_IMG}`);
    const sw = imgPop(page).getByRole('switch');
    await expect(sw).toHaveText('출처 확인된 이미지만');
    await expect(sw).toHaveAttribute('aria-checked', 'true');
    await page.goto(`/_dev/shell?task=1&accepts=image&pop=image&q=${Q_IMG}`);
    await expect(imgPop(page).getByRole('switch')).toHaveCount(0);
    await expect(imgPop(page).locator('.sh-draghint')).toHaveText('끌어서 바로 추가');
  });

  test('I-07 작업 있음 2장 선택 → 푸터 · 대화에 첨부(onAttach 출처 메타)', async ({ page }) => {
    await page.goto(`/_dev/shell?task=1&pop=image&q=${Q_IMG}`);
    const wraps = imgPop(page).locator('.wm-tilewrap');
    await expect(wraps).toHaveCount(6);
    for (const i of [0, 5]) {
      await wraps.nth(i).hover();
      await wraps.nth(i).locator('.wm-tile__check').click();
    }
    // Space 로도 선택/해제
    await tiles(page).nth(2).focus();
    await page.keyboard.press(' ');
    await expect(wraps.nth(2).locator('.wm-tile__check')).toHaveAttribute('aria-pressed', 'true');
    await page.keyboard.press(' ');
    await expect(wraps.nth(2).locator('.wm-tile__check')).toHaveAttribute('aria-pressed', 'false');
    const foot = imgPop(page).locator('[data-footer="task"]');
    await expect(foot).toContainText('선택 2 · 출처 정보가 함께 붙습니다');
    await foot.getByRole('button', { name: '대화에 첨부' }).click();
    await expect.poll(async () => (await devLog(page)).filter((e) => e.kind === 'onAttach').length).toBe(1);
    const att = (await devLog(page)).find((e) => e.kind === 'onAttach') as { count: number; images: Array<Record<string, unknown>> };
    expect(att.count).toBe(2);
    for (const im of att.images) {
      expect((im.source_page as { url: string }).url).toMatch(/^https:\/\/www\.samsung\.com\//);
      expect(im.original_url).toMatch(/^https:\/\/images\.samsung\.com\//);
      expect(typeof im.usage_note).toBe('string');
    }
  });

  test('I-08 작업 없음 → 체크 없음 · 두 버튼 비활성', async ({ page }) => {
    await page.goto(`/?pop=image&q=${Q_IMG}`);
    await expect(tiles(page)).toHaveCount(6);
    await imgPop(page).locator('.wm-tilewrap').first().hover();
    await expect(imgPop(page).locator('.wm-tile__check')).toHaveCount(0);
    const foot = imgPop(page).locator('[data-footer="no-task"]');
    await expect(foot.getByRole('button', { name: '대화에 첨부' })).toBeDisabled();
    await expect(foot.getByRole('button', { name: '현재 작업에 추가' })).toBeDisabled();
  });

  test('I-09 제품 이미지 탭 → 공식 배지만 · 유관 사례 탭 → 도입사례만', async ({ page }) => {
    await page.goto(`/?pop=image&q=${Q_IMG}`);
    await imgPop(page).getByRole('tab', { name: /제품 이미지/ }).click();
    await expect(tiles(page)).toHaveCount(1);
    for (const b of await imgPop(page).locator('.wm-tile__kind').allTextContents()) expect(['제품', '솔루션', '업종']).toContain(b);
    await imgPop(page).getByRole('tab', { name: /유관 사례 이미지/ }).click();
    await expect(tiles(page)).toHaveCount(5);
    for (const b of await imgPop(page).locator('.wm-tile__kind').allTextContents()) expect(b).toBe('도입사례');
    await imgPop(page).getByRole('tab', { name: /내 생성 이미지/ }).click();
    await expect(imgPop(page).getByText('아직 만든 이미지가 없어요.')).toBeVisible();
    await imgPop(page).getByRole('tab', { name: /사내 자산/ }).click();
    await expect(imgPop(page).getByText('등록된 사내 자산이 없어요.')).toBeVisible();
  });

  test('I-x 결과 없음 · X-05 정보 패널 aside', async ({ page }) => {
    await page.goto(`/?pop=image&q=${encodeURIComponent('없는검색어')}`);
    await expect(imgPop(page).getByText('‘없는검색어’에 맞는 이미지가 없어요.')).toBeVisible();
    await expect(page.locator('aside[aria-label="이미지 정보"]')).toHaveCount(1);
  });
});

test.describe('유관 사례 검색 (C)', () => {
  test('C-01 필터 줄 · 유사도 순', async ({ page }) => {
    await page.goto(`/?pop=case&q=${Q_CASE}`);
    const bar = casePop(page).getByRole('group', { name: '사례 필터' });
    await expect(bar.locator('.wm-chip')).toHaveText(['업종: 유통/요식', '제품: 전체', '지역: 전체', '전체 기간 · 삼성 도입사례 198건']);
    await expect(bar).toContainText('유사도 순');
  });

  test('C-02 · C-03 · C-08 업종 유통/요식 + 검색 → 카드 구성', async ({ page }) => {
    await page.goto(`/?pop=case&q=${Q_CASE}`);
    const cards = casePop(page).locator('[data-case-card]');
    await expect(cards).toHaveCount(3);
    for (let i = 0; i < 3; i++) {
      const c = cards.nth(i);
      await expect(c).toContainText(/도입사례 사진 · \d+장/);
      await expect(c.locator('img')).toHaveCount(3);
      await expect(c.locator('.wm-tag').first()).toHaveText(/^유통\/요식/);
      await expect(c).toContainText(/\d{4}-\d{2}-\d{2}/);
      await expect(c.locator('[data-case-url]')).toHaveText(/^samsung\.com\/sec\/business\/insights\/case-study\//);
      await expect(c.getByRole('link', { name: '원문 열기' })).toHaveAttribute('href', /^https:\/\/www\.samsung\.com\/sec\/business\/insights\/case-study\//);
      await expect(c).toContainText('내용 · 사진 출처 삼성전자 고객 도입사례');
      const sum = c.locator('[data-summary]');
      expect(await css(sum, 'height')).toBe('36px');
      expect(await css(sum, 'overflow')).toBe('hidden');
    }
    await expect(cards.first()).toContainText('맥도날드 고양삼송DT점 – 삼성 스마트 사이니지');
  });

  test('C-04 작업 없음 → 원문 열기 새 탭 · 추가 비활성', async ({ page, context }) => {
    await context.route('https://www.samsung.com/**', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<title>case</title>' }));
    await page.goto(`/?pop=case&q=${Q_CASE}`);
    const card = casePop(page).locator('[data-case-card]').first();
    const link = card.getByRole('link', { name: '원문 열기' });
    await expect(link).toHaveAttribute('target', '_blank');
    const [popup] = await Promise.all([page.waitForEvent('popup'), link.click()]);
    expect(popup.url()).toContain('/sec/business/insights/case-study/reference-MCDONALDSsamsong/');
    await popup.close();
    await expect(card.locator('.wm-addbtn')).toBeDisabled();
  });

  test('C-05 기간 최근 3년 → 칩 · 날짜 범위', async ({ page }) => {
    await page.goto(`/?pop=case&q=${Q_CASE}`);
    const d = casePop(page);
    await expect(d.locator('[data-case-card]')).toHaveCount(3);
    await d.locator('[data-filter="period"] .wm-chip').click();
    await d.getByRole('menuitemradio', { name: '최근 3년' }).click();
    await expect(d.locator('[data-filter="period"] .wm-chip')).toHaveText(/^최근 3년 · 삼성 도입사례 (\d+)건$/);
    const n = Number((await d.locator('[data-filter="period"] .wm-chip').textContent())!.match(/(\d+)건/)![1]);
    expect(n).toBeLessThan(198);
    const dates = await d.locator('[data-case-card]').evaluateAll((els) => els.map((e) => (e.textContent ?? '').match(/\d{4}-\d{2}-\d{2}/)?.[0]));
    const cut = new Date('2026-10-06');
    cut.setFullYear(cut.getFullYear() - 3);
    for (const dt of dates) expect(new Date(dt!).getTime()).toBeGreaterThanOrEqual(cut.getTime());
  });

  test('C-06 지역 메뉴는 전체만 · 업종 메뉴', async ({ page }) => {
    await page.goto(`/?pop=case&q=${Q_CASE}`);
    const d = casePop(page);
    await d.locator('[data-filter="region"] .wm-chip').click();
    await expect(d.getByRole('menu').getByRole('menuitemradio')).toHaveText(['전체']);
    await page.keyboard.press('Escape');
    await expect(d.getByRole('menu')).toHaveCount(0);
    await expect(d).toBeVisible();
    await d.locator('[data-filter="vertical"] .wm-chip').click();
    const items = d.getByRole('menu').getByRole('menuitemradio');
    await expect(items.first()).toHaveText('전체');
    await d.getByRole('menuitemradio', { name: '호텔' }).click();
    await expect(d.locator('[data-filter="vertical"] .wm-chip')).toHaveText('업종: 호텔');
  });

  test('C-07 작업 없음 · `호텔 객실 TV 통합 관리` → 업종: 호텔(자동 판별)', async ({ page }) => {
    await page.goto('/?pop=case');
    const d = casePop(page);
    await expect(d.getByText('고객 · 업종 · 용도로 검색해 보세요.')).toBeVisible();
    await d.getByRole('textbox', { name: '사례 검색' }).fill('호텔 객실 TV 통합 관리');
    await expect(d.locator('[data-filter="vertical"] .wm-chip')).toHaveText('업종: 호텔');
  });
});
