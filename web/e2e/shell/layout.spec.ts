/**
 * 00-shell §8.1 레이아웃(L) · §8.2 사이드바(N) · §8.3 홈(H).
 */
import { expect, test } from '@playwright/test';
import { setupShell } from './fixtures/mock';

const GROUPS = ['고객 요구사항', '전략 수립 Storyboard', '이미지 생성', '공간 조감도 생성', '공간 시나리오 생성', 'Market Intelligence', '경쟁사 분석',
  'Value Proposition', 'Spec 시트 생성', 'B2B 제안서 생성'];
const css = (loc: import('@playwright/test').Locator, prop: string) => loc.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);

test.describe('레이아웃 (L)', () => {
  test('L-01 사이드바 260 · 상단바 64 · 메인 1180 · 바탕 #f5f6f8', async ({ page }) => {
    await setupShell(page);
    await page.goto('/');
    const sb = (await page.locator('aside.sh-sidebar').boundingBox())!;
    const tb = (await page.locator('header.sh-topbar').boundingBox())!;
    const main = (await page.locator('main.sh-main').boundingBox())!;
    expect(sb.width).toBe(260);
    expect(tb.height).toBe(64);
    expect(tb.x).toBe(260);
    expect(main.width).toBe(1180);
    expect(await css(page.locator('.sh-root'), 'background-color')).toBe('rgb(245, 246, 248)');
  });

  test('L-02 글꼴은 같은 출처(CDN 없음)', async ({ page, baseURL }) => {
    const urls: string[] = [];
    page.on('request', (r) => urls.push(r.url()));
    await setupShell(page);
    await page.goto('/?pop=product&node=fam_G000182628');
    await expect(page.locator('[data-model]')).toHaveCount(7);
    await page.evaluate(() => document.fonts.ready);
    expect(urls.some((u) => /fonts\.(googleapis|gstatic)\.com/.test(u))).toBe(false);
    const fonts = urls.filter((u) => /\.woff2?(\?|$)/.test(u));
    expect(fonts.length).toBeGreaterThan(0);
    for (const u of fonts) expect(new URL(u).origin).toBe(new URL(baseURL!).origin);
    expect(fonts.some((u) => u.includes('noto-sans-kr'))).toBe(true);
    expect(fonts.some((u) => u.includes('manrope'))).toBe(true);
    expect(await page.evaluate(() => document.fonts.check('14px "Noto Sans KR"'))).toBe(true);
  });

  test('L-03 모든 <img> 는 같은 출처(images.samsung.com 아님)', async ({ page, baseURL }) => {
    await setupShell(page);
    const origin = new URL(baseURL!).origin;
    const check = async () => {
      const srcs = await page.locator('img').evaluateAll((els) => els.map((e) => (e as HTMLImageElement).currentSrc || (e as HTMLImageElement).src).filter(Boolean));
      for (const s of srcs) { expect(new URL(s).origin).toBe(origin); expect(s).not.toContain('images.samsung.com'); }
      return srcs.length;
    };
    for (const url of ['/', '/?pop=product&node=fam_G000182628', '/?pop=image&q=카페 메뉴보드', '/?pop=case&q=프랜차이즈 메뉴보드',
      '/?detail=product:LH55QMCEBGCXKR&tab=images', '/?detail=solution:magicinfo&tab=images', '/?detail=solution:magicinfo&tab=cases']) {
      await page.goto(url);
      await page.waitForLoadState('networkidle');
      await check();
    }
    expect(await check()).toBeGreaterThan(0);
  });

  test('L-04 주 버튼 배경 rgb(20, 40, 160)', async ({ page }) => {
    await setupShell(page);
    await page.goto('/_dev/shell?task=1&pop=product&node=fam_G000182628');
    await page.getByRole('button', { name: '추가 QM55C' }).click();
    const add = page.getByRole('dialog', { name: '제품 탐색' }).getByRole('button', { name: '현재 작업에 추가' });
    await expect(add).toBeEnabled();
    // 켜질 때 배경 전환(.12s)이 끝난 뒤의 색
    await expect.poll(() => css(add, 'background-color')).toBe('rgb(20, 40, 160)');
    await page.goto('/?detail=product:LH55QMCEBGCXKR');
    const spec = page.getByRole('link', { name: 'Spec 시트 만들기' });
    await expect(spec).toBeVisible();
    expect(await css(spec, 'background-color')).toBe('rgb(20, 40, 160)');
  });

  test('L-05 외부 링크는 target=_blank + rel noopener', async ({ page }) => {
    await setupShell(page);
    for (const url of ['/?pop=image&q=카페 메뉴보드', '/?pop=case&q=프랜차이즈 메뉴보드', '/?detail=product:LH55QMCEBGCXKR&tab=spec',
      '/?detail=product:LH55QMCEBGCXKR&tab=cases', '/?detail=solution:magicinfo&tab=cases']) {
      await page.goto(url);
      await expect(page.locator('a[href^="http"]').first()).toBeAttached(); // 검색은 300ms 디바운스 뒤에 온다
      await page.waitForLoadState('networkidle');
      const links = await page.locator('a[href^="http"]').evaluateAll((els) => els.map((a) => ({ t: a.getAttribute('target'), r: a.getAttribute('rel') ?? '', h: a.getAttribute('href') })));
      expect(links.length).toBeGreaterThan(0);
      for (const l of links) { expect(l.t, l.h!).toBe('_blank'); expect(l.r, l.h!).toContain('noopener'); }
    }
  });
});

test.describe('사이드바 (N)', () => {
  test('N-01 · N-02 · N-07 로고 · 새 작업 · 작업 내역 10 · 개수 · 사용자 카드', async ({ page }) => {
    await setupShell(page);
    await page.goto('/');
    const sb = page.locator('aside.sh-sidebar');
    await expect(sb.getByText('winmate', { exact: true })).toBeVisible();
    await expect(sb.getByRole('link', { name: '새 작업' })).toBeVisible();
    await expect(sb.getByText('작업 내역', { exact: true })).toBeVisible();
    await expect(sb.locator('.sh-group__name')).toHaveText(GROUPS);
    await expect(sb.locator('.sh-group__row--open')).toHaveCount(0);
    await expect(sb.locator('[data-group="proposal"] .wm-count')).toHaveText('2');
    await expect(sb.locator('[data-group="storyboard"] .wm-count')).toHaveText('4');
    await expect(sb.locator('.sh-user .wm-avatar')).toHaveText('최');
    await expect(sb.locator('.sh-user__name')).toHaveText('최민섭');
    await expect(sb.locator('.sh-user__org')).toHaveText('Samsung Research · AX그룹');
    await expect(sb.getByRole('button', { name: '설정' })).toBeVisible();
  });

  test('N-03 현재 작업물 라우트 → 그 그룹만 펼침 · 현재 항목 강조', async ({ page }) => {
    await setupShell(page);
    await page.goto('/spec/sp_qmc_qbc');
    const sb = page.locator('aside.sh-sidebar');
    await expect(sb.locator('.sh-group__row--open')).toHaveCount(1);
    const row = sb.locator('[data-group="spec"] .sh-group__row');
    await expect(row).toHaveClass(/sh-group__row--open/);
    expect(await css(row.locator('.sh-group__link'), 'font-weight')).toBe('600');
    expect(await css(row, 'background-color')).toBe('rgb(245, 246, 248)');
    await expect(sb.locator('[data-group="spec"] .sh-item')).toHaveText(['QMC vs QBC 55" 비교', 'The Wall IAB 146" 스펙', 'Flip Pro WA75D 스펙']);
    const cur = sb.getByRole('link', { name: 'QMC vs QBC 55" 비교' });
    await expect(cur).toHaveAttribute('aria-current', 'page');
    expect(await css(cur, 'background-color')).toBe('rgb(234, 238, 251)');
    expect(await css(cur, 'color')).toBe('rgb(20, 40, 160)');
  });

  test('N-04 · N-05 · N-06 그룹 · 항목 · 로고 · 새 작업 이동', async ({ page }) => {
    await setupShell(page);
    await page.goto('/');
    const sb = page.locator('aside.sh-sidebar');
    await sb.getByRole('link', { name: /Market Intelligence/ }).click();
    await expect(page).toHaveURL(/\/mi$/);
    await expect(sb.locator('[data-group="mi"] .sh-group__row')).toHaveClass(/open/);
    await page.goto('/proposal');
    await sb.getByRole('link', { name: 'A 커피 프랜차이즈 메뉴보드 제안' }).click();
    await expect(page).toHaveURL(/\/proposal\/pr_a$/);
    await sb.getByRole('link', { name: 'winmate 홈' }).click();
    await expect(page).toHaveURL(/\/$/);
    await page.goto('/mi');
    await sb.getByRole('link', { name: '새 작업' }).click();
    await expect(page).toHaveURL(/\/$/);
  });

  test('N-08 한 기능에 작업 7개 → 최신 5개 · N-09 긴 제목 말줄임 · 행 32', async ({ page }) => {
    const long = 'A 커피 프랜차이즈 전국 매장 메뉴보드 리뉴얼과 드라이브스루 옥외 사이니지 통합 제안 (2026 하반기)';
    const items = Array.from({ length: 7 }, (_, i) => ({ feature: 'SP', title: i === 0 ? long : `스펙 작업 ${i + 1}`, route: `/spec/sp_${i + 1}`, minutesAgo: (i + 1) * 10 }));
    await setupShell(page, { ws: { items } });
    await page.goto('/spec');
    const its = page.locator('[data-group="spec"] .sh-item');
    await expect(its).toHaveCount(5);
    await expect(its.first()).toHaveAttribute('title', long);
    const box = (await its.first().boundingBox())!;
    expect(box.height).toBe(32);
    const span = its.first().locator('span');
    expect(await css(span, 'text-overflow')).toBe('ellipsis');
    expect(await span.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true);
    await expect(its.nth(4)).toHaveText('스펙 작업 5');
  });
});

test.describe('홈 (H)', () => {
  test('H-01 인사말 시각별(14:00 오후 · 09:00 아침 · 20:00 저녁)', async ({ page }) => {
    for (const [t, g] of [['14:00', '좋은 오후예요'], ['09:00', '좋은 아침이에요'], ['20:00', '좋은 저녁이에요']]) {
      await setupShell(page, { clock: new Date(`2026-10-06T${t}:00+09:00`) });
      await page.goto('/');
      await expect(page.getByRole('heading', { level: 1 })).toHaveText(`${g}, 민섭님. 오늘은 무엇을 제안해 볼까요?`);
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });

  test('H-01b 사용자 정보를 못 받으면 이름 없이', async ({ page }) => {
    await setupShell(page, { ws: { meFails: true } });
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('좋은 오후예요. 오늘은 무엇을 제안해 볼까요?', { timeout: 15_000 });
  });

  test('H-02 · H-03 부제 · B2B 카드', async ({ page }) => {
    await setupShell(page);
    await page.goto('/');
    await expect(page.getByText('만들 콘텐츠를 고르면 바로 시작돼요. 고객 요구사항을 먼저 정리해 두면 이후 작업이 그 내용으로 자동으로 채워져요.')).toBeVisible();
    const hero = page.locator('[data-home-card="proposal"]');
    await expect(hero).toContainText('B2B 제안서 만들기');
    await expect(hero).toContainText('핵심 기능');
    await expect(hero).toContainText('바로 시작');
    await hero.getByText('유형을 고르고').click();
    await expect(page).toHaveURL(/\/proposal\/new$/);
  });

  test('H-04 · H-05 · H-06 기획·분석 6 · 공간·비주얼 3', async ({ page }) => {
    await setupShell(page);
    await page.goto('/');
    const plan = page.locator('[data-home-section="plan"] .hcard');
    await expect(plan).toHaveCount(6);
    const want = [
      ['requirements', '고객 요구사항', '요청서 · 회의록 · 메모를 넣으면 요구사항 정의서로 정리해 드려요.', '모든 콘텐츠가 함께 써요'],
      ['storyboard', '전략 수립 Storyboard', '요구사항을 기획 방향 · 목차 · 요구 추적표로 바꿔요.', '제안서 목차 · 뼈대'],
      ['mi', 'Market Intelligence', '시장 · 고객사 · 사용자를 분석해 삼성의 강점을 찾아요.', '제안서 MI 섹션'],
      ['competitor', '경쟁사 분석', '고객 요구사항이나 한 문단 메모로 경쟁사를 찾고 삼성과 비교해요.', 'MI · Why Samsung 시트'],
      ['vp', 'Value Proposition', '고객 과제 → 가치 → 기대 효과로 핵심 메시지를 세워요.', '제안서 Value Props 섹션'],
      ['spec', 'Spec 시트 생성', '제품을 골라 비교 가능한 스펙 시트를 만들어요.', '제안서 제품 스펙 섹션'],
    ];
    for (let i = 0; i < want.length; i++) {
      const c = plan.nth(i);
      await expect(c).toHaveAttribute('data-home-card', want[i][0]);
      for (const t of want[i].slice(1)) await expect(c).toContainText(t);
      await expect(c).toHaveAttribute('href', `/${want[i][0]}/new`);
    }
    await expect(plan.nth(0)).toContainText('여기서 시작');
    await expect(plan.nth(3)).toContainText('NEW');
    expect(await css(plan.nth(3), 'border-top-color')).toBe('rgb(20, 40, 160)');
    const vis = page.locator('[data-home-section="visual"] .hcard');
    await expect(vis).toHaveCount(3);
    for (const [i, k, t] of [[0, 'image', '이미지 생성'], [1, 'birdseye', '공간 조감도 생성'], [2, 'scenario', '공간 시나리오 생성']] as const) {
      await expect(vis.nth(i)).toContainText(t);
      await expect(vis.nth(i)).toHaveAttribute('href', `/${k}/new`);
    }
    await plan.nth(1).click();
    await expect(page).toHaveURL(/\/storyboard\/new$/);
  });

  test('H-04b NEW 카드 테두리 1.5px #1428a0(작성값 — 크롬은 계산값을 1px 로 내림)', async ({ page }) => {
    await setupShell(page);
    await page.goto('/');
    const c = page.locator('[data-home-card="competitor"]');
    await expect(c).toContainText('NEW');
    expect(await css(c, 'border-top-color')).toBe('rgb(20, 40, 160)');
    const authored = await page.evaluate(() => {
      for (const sh of Array.from(document.styleSheets)) {
        for (const r of Array.from(sh.cssRules)) if (r instanceof CSSStyleRule && r.selectorText === '.hcard--new') return /(^|\s)1\.5px\s/.test(r.style.getPropertyValue('border')) ? '1.5px' : r.style.cssText;
      }
      return null;
    });
    expect(authored).toBe('1.5px');
  });

  test('H-07 · H-09 · H-10 최근 작업 3(최신순) · 시점 · 전체 작업 보기', async ({ page }) => {
    const now = new Date('2026-10-06T14:00:00+09:00');
    const items = [
      { feature: 'RQ', title: 'E 자산운용 용산 AI Ready 오피스', route: '/requirements/rq_e', minutesAgo: 120 },
      { feature: 'SB', title: 'E 자산운용 용산 오피스 제안 기획', route: '/storyboard/sb_e', minutesAgo: 28 * 60 },
      { feature: 'CA', title: 'A 커피 메뉴보드 경쟁사 분석', route: '/competitor/ca_a', minutesAgo: 3 * 24 * 60 },
      { feature: 'MI', title: '오래된 분석', route: '/mi/mi_old', minutesAgo: 40 * 24 * 60 },
    ];
    await setupShell(page, { ws: { now, items } });
    await page.goto('/');
    const rec = page.locator('[data-home-section="recent"] .hcard');
    await expect(rec).toHaveCount(3);
    await expect(rec.nth(0)).toContainText('E 자산운용 용산 AI Ready 오피스');
    await expect(rec.nth(0)).toContainText('고객 요구사항 · 2시간 전');
    await expect(rec.nth(1)).toContainText('전략 수립 Storyboard · 어제');
    await expect(rec.nth(2)).toContainText('경쟁사 분석 · 3일 전');
    await rec.nth(2).click();
    await expect(page).toHaveURL(/\/competitor\/ca_a$/);
    await page.goto('/');
    await page.getByRole('link', { name: '전체 작업 보기' }).click();
    await expect(page).toHaveURL(/\/requirements$/);
    // 40일 전(올해) → M/D
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await setupShell(page, { ws: { now, items: [items[3]] } });
    await page.goto('/');
    await expect(page.locator('[data-home-section="recent"] .hcard').first()).toContainText('Market Intelligence · 8/27');
  });

  test('H-08 작업 0개 → 최근 작업 영역 없음', async ({ page }) => {
    await setupShell(page, { ws: { empty: true } });
    await page.goto('/');
    await expect(page.locator('[data-home-section="plan"] .hcard')).toHaveCount(6);
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('최근 작업')).toHaveCount(0);
    await expect(page.locator('[data-home-section="recent"]')).toHaveCount(0);
  });

  test('H-11 카드 hover(테두리 brand · 위로 1px) · 키보드 포커스 윤곽선', async ({ page }) => {
    await setupShell(page);
    await page.goto('/');
    const card = page.locator('[data-home-card="storyboard"]');
    await card.hover();
    await expect.poll(() => css(card, 'border-top-color')).toBe('rgb(20, 40, 160)');
    await expect.poll(() => css(card, 'transform')).toBe('matrix(1, 0, 0, 1, 0, -1)');
    await page.mouse.move(5, 895);
    await card.focus();
    await page.keyboard.press('Shift+Tab');
    await page.keyboard.press('Tab');
    expect(await css(card, 'outline-style')).toBe('solid');
    expect(await css(card, 'outline-width')).toBe('2px');
  });
});
