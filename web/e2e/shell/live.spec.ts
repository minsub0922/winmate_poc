/**
 * 실제 서비스(흉내 없음) — workspace 는 항상, kb 는 `GET /api/kb/v1/meta` 가 200 일 때만.
 * 숫자는 kb v1(2026-10-04 수집) 기준이지만, 바뀔 수 있는 개수는 kb 응답에서 읽어 비교한다.
 * 결과 화면: e2e/shell/__screens__/live-*.png
 */
import { expect, test, type Page } from '@playwright/test';
import { kbIsUp } from './fixtures/mock';

const shot = (page: Page, name: string) => page.screenshot({ path: `e2e/shell/__screens__/live-${name}.png` });
const dialog = (page: Page, name: string) => page.getByRole('dialog', { name });
const api = async <T,>(page: Page, path: string): Promise<T> => (await page.request.get(path)).json() as Promise<T>;
/** 이미지는 실제 kb 썸네일 — 다 받을 때까지 기다린다 */
const imagesLoaded = (page: Page) => page.waitForFunction(() => [...document.images].every((i) => i.complete), undefined, { timeout: 10_000 }).catch(() => undefined);

let kbUp: boolean | null = null;

test.describe('실제 workspace', () => {
  test('LIVE-01 인사 · 사용자 카드 = /me', async ({ page }) => {
    const me = await api<{ name: string; given_name: string; org: string }>(page, '/api/workspace/v1/me');
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toContainText(`${me.given_name}님`);
    await expect(page.locator('.sh-user__name')).toHaveText(me.name);
    await expect(page.locator('.sh-user__org')).toHaveText(me.org);
    await expect(page.locator('[data-home-section="flow"] [data-home-card]')).toHaveCount(3);
  });
});

test.describe('실제 kb', () => {
  test.beforeEach(async ({ baseURL }) => {
    if (kbUp === null) kbUp = await kbIsUp(baseURL!);
    test.skip(!kbUp, 'kb 서비스가 떠 있지 않음(GET /api/kb/v1/meta ≠ 200)');
  });

  test('LIVE-02 제품 탐색 → QMC 7개 · 상세 시트 3탭', async ({ page }) => {
    await page.goto('/?pop=product&node=fam_G000182628');
    const pop = dialog(page, '제품 탐색');
    await expect(pop.locator('[data-model]')).toHaveCount(7);
    await expect(pop.locator('[data-model] .sh-mname > span:first-child')).toHaveText(['QM32C', 'QM43C', 'QM50C', 'QM55C', 'QM65C', 'QM75C', 'QM85C']);
    await expect(pop.locator('[data-model="LH55QMCEBGCXKR"] [data-col="size"]')).toHaveText('55"');
    await expect(pop.locator('.sh-path')).toHaveText(/사이니지›스마트 LCD 사이니지›QMC Series/);
    await expect(pop.locator('[data-node="fam_G000182628"]')).toHaveAttribute('aria-current', 'true');
    await imagesLoaded(page);
    await shot(page, 'pop-product');

    await pop.getByRole('link', { name: /^QM55C 상세 보기/ }).click();
    const sheet = dialog(page, 'QM55C 제품 상세');
    await expect(sheet).toBeVisible();
    await expect(page).toHaveURL(/detail=product%3ALH55QMCEBGCXKR|detail=product:LH55QMCEBGCXKR/);
    const m = await api<{ spec: { groups: Array<{ name: string; column?: string; rows: Array<{ label: string; value: string }> }> }; counts: { images: number; cases: number } }>(page, '/api/kb/v1/models/LH55QMCEBGCXKR');
    await expect(sheet.locator('[data-spec-group]')).toHaveCount(m.spec.groups.length);
    await expect(sheet.locator('[data-spec-row="대각선"] .sh-spec__v')).toHaveText('138.7 cm (55형)');
    // kb 가 준 열(left · right)대로 두 열
    const leftNames = m.spec.groups.filter((g) => g.column !== 'right').map((g) => g.name);
    const firstCol = sheet.locator('.sh-spec > div').first().locator('[data-spec-group]');
    await expect(firstCol).toHaveCount(leftNames.length);
    for (const [i, n] of leftNames.entries()) await expect(firstCol.nth(i)).toHaveAttribute('data-spec-group', n);
    await expect(sheet.locator('[data-docs-fallback]')).toBeVisible(); // G-PRD-3: 공식 자료 없음 → 제품 페이지 안내
    await imagesLoaded(page);
    await shot(page, 'sheet-product-spec');

    await sheet.getByRole('tab', { name: /이미지/ }).click();
    await expect(sheet.locator('.sh-gallery .wm-tile')).toHaveCount(m.counts.images);
    await expect(sheet.getByLabel('선택한 이미지')).toContainText('정면');
    await imagesLoaded(page);
    await shot(page, 'sheet-product-images');

    await sheet.getByRole('tab', { name: /활용 사례/ }).click();
    const cases = await api<{ default_match?: string; counts: Record<string, number>; items: Array<{ quote?: string | null }> }>(page, '/api/kb/v1/models/LH55QMCEBGCXKR/cases');
    await expect(sheet.locator('[data-case-row]')).toHaveCount(cases.items.length);
    const label = { model: '모델 일치', series: '시리즈 일치', usage: '용도 일치' }[cases.default_match ?? 'usage']!;
    await expect(sheet.getByRole('button', { name: new RegExp(`^${label}`) })).toHaveAttribute('aria-pressed', 'true');
    // 요약(G-CASE-1)이 없으면 원문 인용을 따옴표로
    if (cases.items.some((c) => c.quote)) await expect(sheet.locator('[data-summary="quote"]').first()).toHaveText(/^“.+”$/);
    await imagesLoaded(page);
    await shot(page, 'sheet-product-cases');
  });

  test('LIVE-03 솔루션 11개 · MagicINFO 시트 3탭', async ({ page }) => {
    const list = await api<{ items: Array<{ id: string; name: string }> }>(page, '/api/kb/v1/solutions');
    await page.goto('/?pop=solution');
    const pop = dialog(page, '솔루션 탐색');
    await expect(pop.locator('[data-solution]')).toHaveCount(list.items.length);
    await expect(pop.locator('[data-solution] [data-name]').first()).toHaveText(list.items[0].name);
    await shot(page, 'pop-solution');

    await page.goto('/?detail=solution:magicinfo&tab=overview');
    const sheet = dialog(page, 'MagicINFO 솔루션 상세');
    const d = await api<{ profile: { parts: unknown[]; pillars: unknown[] } | null; counts: { images: number; cases: number } }>(page, '/api/kb/v1/solutions/magicinfo');
    await expect(sheet.locator('[data-part]')).toHaveCount(d.profile?.parts.length ?? 0);
    await expect(sheet.locator('[data-pillar]')).toHaveCount(d.profile?.pillars.length ?? 0);
    await imagesLoaded(page);
    await shot(page, 'sheet-solution-overview');

    await sheet.getByRole('tab', { name: /이미지/ }).click();
    const imgs = await api<{ groups: Array<{ key: string; items: unknown[] }> }>(page, '/api/kb/v1/solutions/magicinfo/images');
    await expect(sheet.locator('[data-image-group]')).toHaveCount(imgs.groups.filter((g) => g.items.length).length);
    await imagesLoaded(page);
    await shot(page, 'sheet-solution-images');

    await sheet.getByRole('tab', { name: /활용 사례/ }).click();
    const cs = await api<{ title_explicit: unknown[]; body_mentions: unknown[] }>(page, '/api/kb/v1/solutions/magicinfo/cases');
    await expect(sheet.locator('[data-case-row]')).toHaveCount(cs.title_explicit.length);
    await expect(sheet.locator('[data-mention]')).toHaveCount(cs.body_mentions.length);
    await imagesLoaded(page);
    await shot(page, 'sheet-solution-cases');
  });

  test('LIVE-04 이미지 검색 — 탭 숫자 = kb counts · 정보 패널', async ({ page }) => {
    const q = '맥도날드 메뉴보드';
    const r = await api<{ counts: { all: number; official: number; case: number } }>(page, `/api/kb/v1/images/search?q=${encodeURIComponent(q)}&source=all&verified_only=true&limit=24`);
    await page.goto(`/?pop=image&q=${encodeURIComponent(q)}`);
    const pop = dialog(page, '이미지 검색');
    await expect(pop.getByRole('tab', { name: /^제품 이미지/ })).toContainText(String(r.counts.official));
    await expect(pop.getByRole('tab', { name: /^유관 사례 이미지/ })).toContainText(String(r.counts.case));
    await expect(pop.locator('.wm-tile').first()).toBeVisible();
    await expect(page.locator('aside[aria-label="이미지 정보"]')).toContainText('출처 페이지');
    await imagesLoaded(page);
    await shot(page, 'pop-image');
    // 다음 쪽(next_cursor) — `더 보기` 로 붙고 포커스는 그대로
    const tiles = pop.locator('.wm-tile');
    const before = await tiles.count();
    if (r.counts.all > before) {
      await tiles.nth(2).click();
      await pop.getByRole('button', { name: /^이미지 더 보기/ }).click();
      await expect.poll(() => tiles.count()).toBeGreaterThan(before);
      await expect(tiles.nth(2)).toHaveAttribute('aria-pressed', 'true');
    }
  });

  test('LIVE-05 사례 검색 — `호텔` → 업종 자동 판별 · 말뭉치 수', async ({ page }) => {
    const meta = await api<{ counts: { case_pages: number } }>(page, '/api/kb/v1/meta');
    await page.goto(`/?pop=case&q=${encodeURIComponent('호텔')}`);
    const pop = dialog(page, '유관 사례 검색');
    await expect(pop.locator('[data-case-card]').first()).toBeVisible();
    await expect(pop.locator('[data-filter="vertical"] .wm-chip')).toHaveText(/업종: 호텔/);
    await expect(pop.locator('[data-filter="period"] .wm-chip')).toContainText(`삼성 도입사례 ${meta.counts.case_pages}건`);
    await imagesLoaded(page);
    await shot(page, 'pop-case');
    const cards = pop.locator('[data-case-card]');
    const before = await cards.count();
    const more = pop.getByRole('button', { name: /^사례 더 보기/ });
    if (await more.count()) {
      await expect(more).toContainText(`${before} / `);
      await more.click();
      await expect.poll(() => cards.count()).toBeGreaterThan(before);
    }
  });

  test('LIVE-06 제품 입력창 — 실제 `/products/search`', async ({ page }) => {
    await page.goto('/_dev/kit');
    const input = page.getByRole('combobox', { name: '제품명 입력' });
    await input.fill('QM55');
    const lb = page.getByRole('listbox', { name: '제품 검색 결과' });
    const first = lb.getByRole('option').first();
    // 모델 행 이름은 표시명(QM55C) — kb `label`(Smart Signage QM55C)이 아니라
    await expect(first.locator('.wm-result__name')).toHaveText('QM55C');
    await expect(first.locator('mark')).toHaveText('QM55');
    await input.press('Enter');
    await expect(page.locator('[data-bubble]')).toHaveText(['QM55C']);
    await expect(page.getByTestId('product-input-value')).toContainText('"ref":"kb:model:mdl_LH55QMCEBGCXKR"');
  });
});
