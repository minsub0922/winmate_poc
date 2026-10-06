/**
 * 00-shell §8.10 제품 상세 시트(PD) · §8.11 솔루션 상세 시트(SD). kb 는 고정 데이터(fixtures/mock.ts).
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { devLog, setupShell } from './fixtures/mock';
import { PDP } from './fixtures/kb-data';

const css = (loc: Locator, prop: string) => loc.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
const productSheet = (page: Page) => page.getByRole('dialog', { name: 'QM55C 제품 상세' });
const solutionSheet = (page: Page) => page.getByRole('dialog', { name: 'MagicINFO 솔루션 상세' });
const meta = (scope: Locator, key: string) => scope.locator(`[data-key="${key}"] .wm-meta__v`);
const QUOTE = 'https://www.samsung.com/sec/business/display-solution/display-solution-bwmip70pa/BW-MIP70PA/';

test.beforeEach(async ({ page }) => { await setupShell(page); });

test.describe('제품 상세 시트 (PD)', () => {
  test('PD-01 1200×828 · (120, 36) · 딤이 사이드바까지 · 팝오버 숨김', async ({ page }) => {
    await page.goto('/?pop=product&detail=product:LH55QMCEBGCXKR');
    const s = productSheet(page);
    await expect(s).toBeVisible();
    const b = (await s.boundingBox())!;
    expect([b.x, b.y, b.width, b.height]).toEqual([120, 36, 1200, 828]);
    const scrim = (await page.getByTestId('sheet-scrim').boundingBox())!;
    expect([scrim.x, scrim.y, scrim.width, scrim.height]).toEqual([0, 0, 1440, 900]);
    await expect(page.getByRole('dialog', { name: '제품 탐색' })).toBeHidden();
  });

  test('PD-02 머리 — 제품 탐색 · 경로 › 모델명 · 제품 페이지 링크 · 상세 닫기', async ({ page }) => {
    await page.goto('/?pop=product&detail=product:LH55QMCEBGCXKR');
    const s = productSheet(page);
    await expect(s.getByRole('button', { name: '제품 탐색' })).toBeVisible();
    await expect(s.getByLabel('경로')).toHaveText(/›QM55C$/);
    await expect(s.getByLabel('경로')).toHaveText('사이니지›스마트 LCD 사이니지›QMC Series›QM55C');
    await expect(s.getByRole('link', { name: 'samsung.com 제품 페이지', exact: true })).toHaveAttribute('href', PDP);
    await expect(s.getByRole('button', { name: '상세 닫기' })).toBeVisible();
  });

  test('PD-03 · PD-04 · PD-05 왼쪽 — 코드 · 부제 · 칩 · 사실 · 대표 이미지 · 썸네일 · 정보 상자', async ({ page }) => {
    await page.goto('/?detail=product:LH55QMCEBGCXKR');
    const s = productSheet(page);
    await expect(s.locator('[data-model-code]')).toHaveText('LH55QMCEBGCXKR');
    await expect(s.locator('[data-title-line]')).toHaveText('단독형 UHD M 시리즈 138.7 cm (55형)');
    await expect(s.getByLabel('핵심').locator('.wm-keychip')).toHaveText(['4K UHD', '500 nit', '24/7', '두께 28.5 mm', 'Tizen 7.0']);
    await expect(s.locator('[data-facts]')).toHaveText('출시 2024년 9월 · 제조국 베트남 · 동작 0~40 ℃');
    await expect(s.locator('.sh-sheet__hero-badge')).toHaveText('1 / 8 · 정면 · 삼성 공식');
    const thumbs = s.locator('.sh-thumb');
    await expect(thumbs).toHaveCount(8);
    expect(await css(thumbs.nth(0), 'border-top-color')).toBe('rgb(20, 40, 160)');
    expect(await css(thumbs.nth(0), 'border-top-width')).toBe('2px');
    for (let i = 1; i < 8; i++) expect(await css(thumbs.nth(i), 'border-top-color')).not.toBe('rgb(20, 40, 160)');
    await expect(s.locator('.sh-srcline')).toHaveText('이미지 출처 · samsung.com 제품 페이지 · 2026-10-04 수집');
    await expect(s.locator('.wm-infobox')).toContainText('CMS — MagicINFO · VXT 지원');
    await s.getByRole('button', { name: 'MagicINFO 상세 →' }).click();
    await expect(page).toHaveURL(/detail=solution(%3A|:)magicinfo/);
    await expect(solutionSheet(page)).toBeVisible();
  });

  test('PD-06 · PD-07 · PD-08 · PD-09 탭 · 확인일 · 스펙 두 열 · 출처 · 공식 자료 안내', async ({ page }) => {
    await page.goto('/?detail=product:LH55QMCEBGCXKR&tab=spec');
    const s = productSheet(page);
    const tabs = s.getByRole('tablist', { name: '상세 항목' });
    await expect(tabs.getByRole('tab')).toHaveText(['스펙 · 자료', '이미지8', '활용 사례3']);
    await expect(tabs).toContainText('공식 정보 확인 2026-10-04');
    const cols = s.locator('.sh-spec > div');
    await expect(cols.nth(0).locator('[data-spec-group]')).toHaveCount(3);
    for (const [i, n] of ['디스플레이', '전원', '크기 · 무게'].entries()) await expect(cols.nth(0).locator('[data-spec-group]').nth(i)).toHaveAttribute('data-spec-group', n);
    for (const [i, n] of ['연결성', '운영 · 환경', '인증 · 액세서리'].entries()) await expect(cols.nth(1).locator('[data-spec-group]').nth(i)).toHaveAttribute('data-spec-group', n);
    const v = (k: string) => s.locator(`[data-spec-row="${k}"] .sh-spec__v`);
    await expect(v('밝기 (Typ)')).toHaveText('500 nit');
    await expect(v('HDMI')).toHaveText('입력 3 · 버전 2 · HDCP 2.2');
    await expect(v('소비전력')).toHaveText('154 W · 대기 0.5 W');
    await expect(v('무게')).toHaveText('15.7 kg · 포장 19.9 kg');
    await expect(v('KC 인증')).toHaveText('R-R-SEC-LH55QMCE');
    await expect(s.getByRole('link', { name: /출처 samsung.com 스펙/ })).toHaveAttribute('href', PDP);
    const fallback = s.locator('[data-docs-fallback]');
    await expect(fallback).toHaveText(/공식 자료는 samsung.com 제품 페이지의 '매뉴얼'에서 확인하세요/);
    await expect(fallback).toHaveAttribute('href', PDP);
  });

  test('PD-10 이미지 탭 — 타일 8 · 첫 타일 포커스 · 패널 키 순서 · 첫 이미지 값', async ({ page }) => {
    await page.goto('/?detail=product:LH55QMCEBGCXKR&tab=images');
    const s = productSheet(page);
    const tiles = s.locator('.sh-gallery .wm-tile');
    await expect(tiles).toHaveCount(8);
    await expect(tiles.nth(0)).toHaveAttribute('aria-pressed', 'true');
    const panel = s.getByLabel('선택한 이미지');
    await expect(panel.locator('[data-key]')).toHaveCount(10);
    const keys = await panel.locator('[data-key]').evaluateAll((els) => els.map((e) => e.getAttribute('data-key')));
    expect(keys).toEqual(['이미지명', '출처 유형', '출처 페이지', '원본 파일', '원본', '저장본', '원본 등록', '수집', '사용 조건', '사용 이력']);
    await expect(meta(panel, '이미지명')).toHaveText('단독형 UHD M 시리즈 정면 (원문 대체 텍스트)');
    await expect(meta(panel, '출처 유형')).toHaveText('삼성전자 공식 · 제품 갤러리');
    await expect(meta(panel, '원본 등록')).toHaveText('2023-08-29 (파일 경로 기준)');
    await expect(meta(panel, '사용 이력')).toHaveText('Winmate 제안서 0건');
    // 다른 타일 → URL img · 패널이 바뀐다
    await tiles.nth(1).click();
    await expect(page).toHaveURL(/img=img_/);
    await expect(tiles.nth(1)).toHaveAttribute('aria-pressed', 'true');
    await expect(tiles.nth(0)).toHaveAttribute('aria-pressed', 'false');
  });

  test('PD-11 왼쪽 세 번째 썸네일 → 이미지 탭 · 세 번째 타일 포커스', async ({ page }) => {
    await page.goto('/?detail=product:LH55QMCEBGCXKR&tab=spec');
    const s = productSheet(page);
    await s.locator('.sh-thumb').nth(2).click();
    await expect(s.getByRole('tab', { name: /이미지/ })).toHaveAttribute('aria-selected', 'true');
    await expect(page).toHaveURL(/tab=images/);
    await expect(s.locator('.sh-gallery .wm-tile').nth(2)).toHaveAttribute('aria-pressed', 'true');
  });

  test('PD-12 활용 사례 — 제목 · 칩 · 말뭉치 · 카드 배지 · 출처 주석', async ({ page }) => {
    await page.goto('/?detail=product:LH55QMCEBGCXKR&tab=cases');
    const s = productSheet(page);
    await expect(s.locator('.sh-summary__title')).toHaveText('QM55C · QMC 시리즈가 본문에 나오는 도입사례는 아직 없습니다');
    await expect(s.getByRole('button', { name: /^모델 일치/ })).toHaveText('모델 일치0');
    await expect(s.getByRole('button', { name: /^시리즈 일치/ })).toHaveText('시리즈 일치0');
    const usage = s.getByRole('button', { name: /^용도 일치/ });
    await expect(usage).toHaveAttribute('aria-pressed', 'true');
    expect(Number((await usage.locator('.wm-num').textContent()) ?? 0)).toBeGreaterThanOrEqual(1);
    await expect(s.locator('.sh-summary__body')).toContainText('삼성 고객 도입사례 198건(본문 있는 사례,');
    const rows = s.locator('[data-case-row]');
    const n = await rows.count();
    expect(n).toBeGreaterThanOrEqual(1);
    for (let i = 0; i < n; i++) {
      await expect(rows.nth(i)).toContainText('도입사례 사진');
      await expect(rows.nth(i).locator('.wm-badge--dashed')).toHaveText(/^용도 일치 · /);
    }
    await expect(s.getByText('사례 내용 · 사진 출처: 삼성전자 고객 도입사례 (samsung.com) · 요약은 원문을 줄여 쓴 것')).toBeVisible();
  });

  test('PD-13 `제품 탐색` → 시트 닫힘 · 제품 탐색이 fam_G000182628(7행)로', async ({ page }) => {
    await page.goto('/?detail=product:LH55QMCEBGCXKR');
    await productSheet(page).getByRole('button', { name: '제품 탐색' }).click();
    await expect(productSheet(page)).toHaveCount(0);
    const pop = page.getByRole('dialog', { name: '제품 탐색' });
    await expect(pop).toBeVisible();
    await expect(page).toHaveURL(/node=fam_G000182628/);
    await expect(pop.locator('[data-model]')).toHaveCount(7);
    await expect(pop.locator('[data-node="fam_G000182628"]')).toHaveAttribute('aria-current', 'true');
  });

  test('PD-14 닫기 · Esc → 시트 닫힘 · 팝오버에서 열었으면 팝오버가 다시', async ({ page }) => {
    await page.goto('/?pop=product&node=fam_G000182628');
    const pop = page.getByRole('dialog', { name: '제품 탐색' });
    await pop.getByRole('link', { name: /^QM55C 상세 보기/ }).click();
    await expect(productSheet(page)).toBeVisible();
    await expect(pop).toBeHidden();
    await page.keyboard.press('Escape');
    await expect(productSheet(page)).toHaveCount(0);
    await expect(pop).toBeVisible();
    await expect(page).not.toHaveURL(/detail=/);
    await pop.getByRole('link', { name: /^QM55C 상세 보기/ }).click();
    await productSheet(page).getByRole('button', { name: '상세 닫기' }).click();
    await expect(productSheet(page)).toHaveCount(0);
    await expect(pop).toBeVisible();
    // 홈에서 바로 연 시트는 닫으면 아무 팝오버도 없다
    await page.goto('/?detail=product:LH55QMCEBGCXKR');
    await productSheet(page).getByRole('button', { name: '상세 닫기' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
  });

  test('PD-15 작업 없음 → 추가 버튼 비활성 · title / 작업 있음 → onAdd', async ({ page }) => {
    await page.goto('/?detail=product:LH55QMCEBGCXKR&tab=images');
    const s = productSheet(page);
    for (const name of ['현재 작업에 추가', '작업에 추가']) {
      const b = s.getByRole('button', { name, exact: true });
      await expect(b).toBeDisabled();
      await expect(b).toHaveAttribute('title', '진행 중인 작업이 없습니다');
    }
    await page.goto('/_dev/shell?task=1&accepts=product,image&detail=product:LH55QMCEBGCXKR&tab=images');
    await productSheet(page).getByRole('button', { name: '현재 작업에 추가', exact: true }).click();
    await expect(productSheet(page).getByRole('button', { name: '✓ 추가됨' }).first()).toBeVisible();
    await productSheet(page).getByRole('button', { name: '작업에 추가', exact: true }).click();
    await expect.poll(async () => (await devLog(page)).filter((e) => e.kind === 'onAdd').map((e) => [e.type, (e.refs as string[])[0]])).toEqual([
      ['product', 'kb:model:mdl_LH55QMCEBGCXKR'], ['image', 'kb:image:img_9ec6148d2e4d9c18'],
    ]);
  });

  test('PD-16 `Spec 시트 만들기` → /spec/new?models=LH55QMCEBGCXKR', async ({ page }) => {
    await page.goto('/?detail=product:LH55QMCEBGCXKR');
    await productSheet(page).getByRole('link', { name: 'Spec 시트 만들기' }).click();
    await expect(page).toHaveURL(/\/spec\/new\?models=LH55QMCEBGCXKR$/);
  });

  test('PD-17 Tab 을 계속 눌러도 포커스가 시트 밖으로 나가지 않는다 · 첫 포커스는 선택된 탭', async ({ page }) => {
    await page.goto('/?detail=product:LH55QMCEBGCXKR&tab=spec');
    const s = productSheet(page);
    await expect(s.getByRole('tab', { name: '스펙 · 자료' })).toBeFocused();
    for (let i = 0; i < 40; i++) {
      await page.keyboard.press('Tab');
      expect(await s.evaluate((el) => el.contains(document.activeElement))).toBe(true);
    }
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Shift+Tab');
      expect(await s.evaluate((el) => el.contains(document.activeElement))).toBe(true);
    }
    // 탭 묶음은 화살표로 옮긴다
    await s.getByRole('tab', { name: '스펙 · 자료' }).focus();
    await page.keyboard.press('ArrowRight');
    await expect(s.getByRole('tab', { name: /이미지/ })).toBeFocused();
    await expect(page).toHaveURL(/tab=images/);
  });

  test('PD-x 없는 모델 → 오류 · 다시 시도 · 닫기', async ({ page }) => {
    await page.goto('/?detail=product:NOPE');
    const s = page.getByRole('dialog', { name: 'NOPE 제품 상세' });
    await expect(s.getByRole('alert')).toContainText('제품 정보를 불러오지 못했어요.');
    await s.getByRole('alert').getByRole('button', { name: '닫기' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
  });
});

test.describe('솔루션 상세 시트 (SD)', () => {
  test('SD-01 · SD-02 머리 링크 · 왼쪽 요약 · 지원 기기 → 제품 시트', async ({ page }) => {
    await page.goto('/?pop=solution&detail=solution:magicinfo');
    const s = solutionSheet(page);
    await expect(s.getByRole('link', { name: '견적 문의 페이지 ↗' })).toHaveAttribute('href', QUOTE);
    await expect(s.getByRole('link', { name: 'samsung.com 소개 페이지 ↗' })).toHaveAttribute('href', 'https://www.samsung.com/sec/business/display-solutions/magicinfo/');
    const left = s.getByLabel('솔루션 요약');
    await expect(left.locator('.sh-idname')).toHaveText('MagicINFO');
    await expect(left.locator('.sh-idcode')).toHaveText('MagicINFO™ 8');
    await expect(left).toContainText('삼성 스마트 사이니지 콘텐츠 관리 솔루션 (CMS)');
    await expect(left.locator('.wm-keychip')).toHaveCount(3);
    await expect(left.locator('[data-purchase]')).toContainText('BW-MIP70PA');
    await expect(left.locator('[data-purchase]')).toContainText('[견적 확인]');
    await expect(left.locator('.wm-infobox')).toContainText('지원 기기 — 삼성 스마트 사이니지');
    await left.getByRole('button', { name: 'QM55C 상세 →' }).click();
    await expect(productSheet(page)).toBeVisible();
    await expect(page).toHaveURL(/detail=product(%3A|:)LH55QMCEBGCXKR/);
  });

  test('SD-03 개요 · 구성 — 기둥 3 · 구성 요소 4 · 배포 2(근거) · 기기 관리 칩 4 · 출처 주석', async ({ page }) => {
    await page.goto('/?detail=solution:magicinfo&tab=overview');
    const s = solutionSheet(page);
    await expect(s.locator('[data-pillar]')).toHaveCount(3);
    expect(await s.locator('[data-pillar]').evaluateAll((els) => els.map((e) => e.getAttribute('data-pillar')))).toEqual(['콘텐츠 관리', '디바이스 관리', '데이터 관리']);
    expect(await s.locator('[data-part]').evaluateAll((els) => els.map((e) => e.getAttribute('data-part')))).toEqual(['MagicINFO Author', 'MagicINFO Server', 'MagicINFO Player', 'MagicINFO Datalink']);
    const deploy = s.locator('[data-deploy]');
    await expect(deploy).toHaveCount(2);
    for (let i = 0; i < 2; i++) await expect(deploy.nth(i)).toContainText('근거 · ');
    await expect(s.locator('[data-device-functions] .wm-minichip')).toHaveCount(4);
    await expect(s.getByText(/^출처 · samsung.com MagicINFO 소개 페이지/)).toBeVisible();
  });

  test('SD-04 활용 사례 — 17건 · 제목에 명시 3 · 본문 언급 14 · 사례 페이지 링크', async ({ page }) => {
    await page.goto('/?detail=solution:magicinfo&tab=cases');
    const s = solutionSheet(page);
    await expect(s.locator('.sh-summary__title')).toHaveText('본문에 MagicINFO가 나오는 도입사례 17건');
    await expect(s.locator('.sh-summary__body')).toContainText('제목에 명시 3건 · 본문 언급 14건');
    const rows = s.locator('[data-case-row]');
    await expect(rows).toHaveCount(3);
    for (let i = 0; i < 3; i++) await expect(rows.nth(i).locator('.wm-ellipsis').first()).toHaveText(/MagicINFO|매직인포/i);
    const mentions = s.locator('[data-mention]');
    await expect(mentions).toHaveCount(14);
    const hrefs = await s.locator('[data-case-row] a[href^="http"], [data-mention]').evaluateAll((els) => els.map((e) => e.getAttribute('href') ?? ''));
    for (const h of hrefs) expect(h.startsWith('https://www.samsung.com/sec/business/insights/case-study/'), h).toBe(true);
  });

  test('SD-05 이미지 — 그룹 머리 · 탭 숫자 = n + m', async ({ page }) => {
    await page.goto('/?detail=solution:magicinfo&tab=images');
    const s = solutionSheet(page);
    const official = s.locator('[data-image-group="official"]');
    const cases = s.locator('[data-image-group="case"]');
    await expect(official.locator('> span').first()).toHaveText(/^공식 소개 이미지 \d+ · /);
    await expect(cases.locator('> span').first()).toHaveText(/^도입사례 사진 \d+ · samsung.com 고객 도입사례$/);
    const n = await official.locator('.wm-tile').count();
    const m = await cases.locator('.wm-tile').count();
    await expect(s.getByRole('tab', { name: /이미지/ }).locator('.wm-tab__n')).toHaveText(String(n + m));
    // 도입사례 사진을 고르면 배지 · 사용 조건이 바뀐다
    await cases.locator('.wm-tile').first().click();
    const panel = s.getByLabel('선택한 이미지');
    await expect(panel).toContainText('도입사례 사진');
    await expect(meta(panel, '사용 조건')).toHaveText('“도입사례 사진” 표기 필수 · 대외 사용 범위 확인 필요');
  });

  test('SD-06 `솔루션 탐색` → 시트 닫힘 · 솔루션 탐색 열림', async ({ page }) => {
    await page.goto('/?detail=solution:magicinfo');
    await solutionSheet(page).getByRole('button', { name: '솔루션 탐색' }).click();
    await expect(solutionSheet(page)).toHaveCount(0);
    await expect(page.getByRole('dialog', { name: '솔루션 탐색' })).toBeVisible();
    await expect(page).toHaveURL(/pop=solution/);
  });

  test('SD-07 프로필 없는 솔루션(knox_capture) → 오류 없이 열리고 개요는 빈 상태', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto('/?detail=solution:knox_capture');
    const s = page.getByRole('dialog', { name: 'Knox Capture 솔루션 상세' });
    await expect(s).toBeVisible();
    await expect(s.locator('[data-overview-empty]')).toBeVisible();
    await expect(s.getByRole('button', { name: /견적 문의 페이지 열기/ })).toBeDisabled();
    expect(errors).toEqual([]);
    // 메시지만 있는 솔루션은 원문 메시지로 대신한다
    await page.goto('/?detail=solution:dex');
    await expect(page.getByRole('dialog', { name: 'Samsung DeX 솔루션 상세' })).toContainText('KB 메시지(원문 그대로)');
  });
});
