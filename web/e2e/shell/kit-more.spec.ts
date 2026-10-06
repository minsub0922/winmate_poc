/**
 * 기능 요청으로 더한 키트 부품(docs/requests/workspace.md) — `/_dev/kit` 아래 견본(MoreKit).
 * 분할 버튼(tone · h · variant) · 큰 스위치 · 선택 카드 · Q 상자 · 키맨 가중치 · 판단 모드 · 출처 카드 · 근거 패널 · 메아리 · 수량 칩 · 오른쪽 시트 · 작업 고르기.
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { setupShell } from './fixtures/mock';

const css = (l: Locator, prop: string) => l.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
const box = async (l: Locator) => (await l.boundingBox())!;

async function open(page: Page) {
  await setupShell(page);
  await page.goto('/_dev/kit');
  await expect(page.getByTestId('kit-more')).toBeVisible();
}

test.describe('키트 더하기 (KIT2)', () => {
  test('KIT2-01 분할 버튼 — brand h32(선택 700) · h28 · line h26(파랑 채움) · 진한 트랙 · 비활성 이유', async ({ page }) => {
    await open(page);
    const g1 = page.getByRole('group', { name: '제안 방향' });
    const on = g1.getByRole('button', { name: '컨셉 제안' });
    await expect(on).toHaveAttribute('aria-pressed', 'true');
    expect(await css(on, 'color')).toBe('rgb(20, 40, 160)');
    expect(await css(on, 'font-weight')).toBe('700');
    expect((await box(on)).height).toBe(32);
    const off = g1.getByRole('button', { name: '공통 Pitch deck' });
    expect(await css(off, 'color')).toBe('rgb(89, 97, 112)');
    await off.click();
    await expect(off).toHaveAttribute('aria-pressed', 'true');
    const g2 = page.getByRole('group', { name: '보기' });
    const cmp = g2.getByRole('button', { name: '전/후 비교' });
    expect((await box(cmp)).height).toBe(28);
    expect(await css(cmp, 'font-weight')).toBe('600');
    expect(await css(g2.getByRole('button', { name: '편집' }), 'color')).toBe('rgb(61, 68, 82)');
    const g3 = page.getByRole('group', { name: '강도' });
    const two = g3.getByRole('button', { name: '2' });
    expect(await css(two, 'background-color')).toBe('rgb(20, 40, 160)');
    expect((await box(two)).width).toBe(30);
    expect((await box(two)).height).toBe(26);
    const g4 = page.getByRole('group', { name: '범위' });
    expect(await css(g4, 'background-color')).toBe('rgb(233, 235, 239)');
    await expect(g4.getByRole('button', { name: '선택한 섹션' })).toBeDisabled();
    await expect(g4.getByRole('button', { name: '선택한 섹션' })).toHaveAttribute('title', '섹션을 먼저 고르세요');
  });

  test('KIT2-02 큰 스위치(36×22) — 누르기 · Space · 비활성', async ({ page }) => {
    await open(page);
    const sw = page.getByRole('switch', { name: '경쟁사 A 포함' });
    const track = sw.locator('.wm-toggle__track');
    expect(await box(track)).toMatchObject({ width: 36, height: 22 });
    await expect(sw).toHaveAttribute('aria-checked', 'false');
    await sw.click();
    await expect(sw).toHaveAttribute('aria-checked', 'true');
    await expect.poll(() => css(track, 'background-color')).toBe('rgb(20, 40, 160)'); // 전환(.12s) 뒤
    await sw.focus();
    await page.keyboard.press(' ');
    await expect(sw).toHaveAttribute('aria-checked', 'false');
    const fixed = page.getByRole('switch', { name: '고정 기준' });
    await expect(fixed).toHaveAttribute('aria-disabled', 'true');
    await fixed.click({ force: true }); // aria-disabled — 눌러도 그대로
    await expect(fixed).toHaveAttribute('aria-checked', 'true');
  });

  test('KIT2-03 선택 카드 — 순서 있는 복수(파란 원 순번) · 라디오 · 선택 테두리 2px + 그림자 · 직접 입력', async ({ page }) => {
    await open(page);
    const c1 = page.getByTestId('choice-concept');
    await expect(c1).toHaveAttribute('aria-pressed', 'true');
    await expect(c1).toHaveAttribute('data-order', '1');
    expect(await css(c1, 'border-top-width')).toBe('2px');
    expect(await css(c1, 'border-top-color')).toBe('rgb(20, 40, 160)');
    expect(await css(c1, 'box-shadow')).toContain('rgba(20, 40, 160, 0.1)');
    expect((await box(c1)).height).toBeGreaterThanOrEqual(58);
    await expect(c1).toContainText('Overview 목적');
    const c2 = page.getByTestId('choice-scope');
    await expect(c2).toHaveAttribute('aria-pressed', 'false');
    await c2.click();
    await expect(c2).toHaveAttribute('data-order', '2');
    await expect(c2).toContainText('2');
    await c1.click(); // 첫째를 빼면 둘째가 1번
    await expect(c2).toHaveAttribute('data-order', '1');
    const etc = page.getByRole('textbox', { name: '직접 입력' });
    await etc.fill('다음 미팅 일정');
    await etc.press('Enter');
    await expect(page.getByTestId('choice-etc')).toHaveText('다음 미팅 일정');
    const pdf = page.getByTestId('choice-pdf');
    expect((await box(pdf)).height).toBe(84);
    await pdf.click();
    await expect(pdf).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByTestId('choice-pptx')).toHaveAttribute('aria-pressed', 'false');
    await expect(pdf.locator('.wm-choice__right b')).toHaveText('12');
  });

  test('KIT2-04 Q 상자 — 크기 · 주 버튼 안 흰 테두리', async ({ page }) => {
    await open(page);
    const qs = page.getByTestId('kit-q').locator('.wm-q');
    await expect(qs).toHaveCount(5);
    const sizes = await qs.evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().width)));
    expect(sizes).toEqual([16, 18, 20, 26, 20]);
    expect(await css(qs.nth(2), 'border-top-color')).toBe('rgb(20, 40, 160)');
    expect(await css(qs.nth(4), 'border-top-color')).toBe('rgb(255, 255, 255)');
    expect(await css(qs.nth(2), 'font-family')).toContain('Manrope');
  });

  test('KIT2-05 키맨 가중치 — 키맨 색 토큰 · 경계 끌기(1%, 각 ≥ 5) · ←/→ · − / + 스테퍼(5 단위)', async ({ page }) => {
    await open(page);
    const bar = page.getByTestId('kit-wbar').locator('.wm-wbar');
    await bar.scrollIntoViewIfNeeded();
    await expect(bar).toHaveAttribute('data-weights', '50,30,20');
    const segs = bar.locator('.wm-wbar__seg');
    expect(await css(segs.nth(0), 'background-color')).toBe('rgb(20, 40, 160)');
    expect(await css(segs.nth(1), 'background-color')).toBe('rgb(84, 104, 216)');
    expect(await css(segs.nth(2), 'background-color')).toBe('rgb(201, 209, 242)');
    expect(await css(segs.nth(2), 'color')).toBe('rgb(20, 40, 160)');
    // 끌기: 첫 경계를 오른쪽으로 폭의 10%
    const h = page.getByRole('slider', { name: '김 상무 · 이 팀장 경계' });
    const b = await box(bar);
    const hb = await box(h);
    await page.mouse.move(hb.x + hb.width / 2, hb.y + hb.height / 2);
    await page.mouse.down();
    await page.mouse.move(hb.x + hb.width / 2 + b.width * 0.1, hb.y + hb.height / 2, { steps: 5 });
    await page.mouse.up();
    await expect(bar).toHaveAttribute('data-weights', '60,20,20');
    // 끝까지 끌어도 이웃은 5 이상
    const hb2 = await box(h);
    await page.mouse.move(hb2.x + hb2.width / 2, hb2.y + hb2.height / 2);
    await page.mouse.down();
    await page.mouse.move(hb2.x + b.width, hb2.y + hb2.height / 2, { steps: 5 });
    await page.mouse.up();
    await expect(bar).toHaveAttribute('data-weights', '75,5,20');
    // 키보드
    await h.focus();
    await page.keyboard.press('ArrowLeft');
    await expect(bar).toHaveAttribute('data-weights', '74,6,20');
    // 스테퍼: 박 책임 + → 25(나머지는 비율대로)
    await page.getByRole('button', { name: '박 책임 가중치 높이기' }).click();
    await expect(bar).toHaveAttribute('data-weights', '69,6,25');
    await expect(page.getByTestId('wstep-k3')).toContainText('25%');
    await page.getByRole('button', { name: '이 팀장 가중치 낮추기' }).click();
    await expect(page.getByTestId('wstep-k2')).toContainText('5%');
  });

  test('KIT2-06 판단 모드 칩 — 보드 글 · 모양 · 흐림', async ({ page }) => {
    await open(page);
    const m = page.getByTestId('kit-modes').locator('.wm-mode');
    await expect(m).toHaveText(['자동', '확인 권장', '선택 필요', '고정', '묻기', '자동']);
    expect(await css(m.nth(0), 'background-color')).toBe('rgb(234, 238, 251)');
    expect(await css(m.nth(1), 'border-top-color')).toBe('rgb(20, 40, 160)');
    expect(await css(m.nth(2), 'background-color')).toBe('rgb(18, 20, 23)');
    expect(await css(m.nth(5), 'opacity')).toBe('0.45');
    expect((await box(m.nth(0))).height).toBe(22);
  });

  test('KIT2-07 근거 패널 · 출처 카드 — 필터 탭 · 선택한 주장 · 하이라이트 · 확인 필요 테두리 · 닫기', async ({ page }) => {
    await open(page);
    const p = page.getByRole('complementary', { name: '출처 · 근거' });
    await expect(p).toBeVisible();
    expect((await box(p)).width).toBe(420);
    await expect(p.getByTestId('evidence-selected')).toContainText('선택한 주장');
    const tabs = p.getByRole('tablist', { name: '출처 종류' }).getByRole('tab');
    await expect(tabs).toHaveCount(3);
    await expect(tabs.first()).toHaveAttribute('aria-selected', 'true');
    await tabs.nth(1).click();
    await expect(tabs.nth(1)).toHaveAttribute('aria-selected', 'true');
    const c1 = p.getByTestId('scard-1');
    await expect(c1.locator('mark')).toHaveText('[00]% 증가');
    await expect(c1).toContainText('원문 일치');
    const c2 = p.getByTestId('scard-2');
    await expect(c2).toContainText('확인 필요');
    expect(await css(c2, 'border-top-color')).toBe('rgb(18, 20, 23)');
    await expect(c2).toContainText('수치 없이 흐름만');
    await c1.getByRole('button', { name: '각주로 복사' }).click();
    await expect(page.getByText('각주로 복사', { exact: true }).last()).toBeVisible();
    await page.screenshot({ path: 'e2e/shell/__screens__/kit-evidence.png' });
    await p.getByRole('button', { name: '패널 닫기' }).click();
    await expect(p).toHaveCount(0);
  });

  test('KIT2-08 메아리 말풍선 · W 말풍선 아래 작업 영역', async ({ page }) => {
    await open(page);
    const echo = page.getByTestId('kit-echo');
    await expect(echo).toHaveText('공간 · 카페 · 매장 메뉴보드 3면, 아침 시간대');
    expect(await css(echo, 'background-color')).toBe('rgb(240, 242, 245)');
    expect(await css(echo, 'border-bottom-right-radius')).toBe('4px');
    expect(await css(echo, 'border-top-left-radius')).toBe('16px');
    expect(await css(echo.locator('b'), 'font-weight')).toBe('600');
    const row = await box(echo);
    const container = await box(page.getByTestId('kit-more'));
    expect(Math.round(row.x + row.width)).toBeGreaterThan(Math.round(container.x + container.width - 60)); // 오른쪽 정렬
    await expect(page.getByTestId('kit-chat-body')).toBeVisible();
  });

  test('KIT2-09 수량 칩 — 제품을 넣으면 ×1 · 눌러 3 · 머리 글 바꾸기', async ({ page }) => {
    await open(page);
    const wrap = page.getByTestId('product-input-qty');
    const input = wrap.getByRole('combobox');
    await input.fill('QM55C');
    const panel = page.getByRole('listbox', { name: '제품 검색 결과' });
    await expect(panel).toBeVisible();
    await expect(panel.locator('[data-results-head]')).toHaveText('"QM55C" 검색 결과 · Enter로 추가');
    await input.press('Enter');
    const qtyBtn = wrap.getByRole('button', { name: /수량 바꾸기$/ });
    await expect(qtyBtn).toHaveText('×1');
    await expect(qtyBtn).toHaveAttribute('title', '수량 바꾸기');
    await qtyBtn.click();
    const menu = wrap.getByRole('menu');
    await expect(menu.getByRole('menuitemradio')).toHaveCount(9);
    await menu.getByRole('menuitemradio', { name: '3' }).click();
    await expect(qtyBtn).toHaveText('×3');
    await expect(menu).toHaveCount(0);
    await expect(page.getByTestId('product-input-qty-value')).toContainText('"qty":3');
    // Esc 로 메뉴 닫기
    await qtyBtn.click();
    await expect(wrap.getByRole('menu')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(wrap.getByRole('menu')).toHaveCount(0);
  });

  test('KIT2-10 오른쪽 시트 — 오른쪽에 붙은 높이 100% · Esc · 딤 클릭', async ({ page }) => {
    await open(page);
    await page.getByRole('button', { name: '규칙 시트 열기' }).click();
    const d = page.getByRole('dialog', { name: '에이전트 라우팅 규칙' });
    await expect(d).toBeVisible();
    await expect(d).toHaveAttribute('data-variant', 'side');
    const vw = page.viewportSize()!;
    // 밀려 들어오는 움직임(.18s)이 끝난 뒤
    await expect.poll(async () => { const bb = await box(d); return Math.round(bb.x + bb.width); }).toBe(vw.width);
    const b = await box(d);
    expect(Math.round(b.height)).toBe(vw.height);
    expect(Math.round(b.width)).toBe(640);
    await page.screenshot({ path: 'e2e/shell/__screens__/kit-side-sheet.png' });
    await page.keyboard.press('Escape');
    await expect(d).toHaveCount(0);
    await page.getByRole('button', { name: '규칙 시트 열기' }).click();
    await page.mouse.click(40, 400); // 딤
    await expect(page.getByRole('dialog', { name: '에이전트 라우팅 규칙' })).toHaveCount(0);
  });

  test('KIT2-11 작업 고르기 — 목록(workspace items) · 고르기 전 확인 꺼짐 · ↓ · Enter', async ({ page }) => {
    await open(page);
    await page.getByRole('button', { name: 'Storyboard 고르기' }).click();
    const d = page.getByRole('dialog', { name: 'Storyboard 고르기' });
    const opts = d.getByRole('option');
    await expect(opts).toHaveCount(4);
    await expect(opts.first()).toContainText('E 자산운용 용산 오피스 제안 기획');
    const go = d.getByRole('button', { name: '이 자료로 시작' });
    await expect(go).toBeDisabled();
    await expect(go).toHaveAttribute('title', '작업을 골라 주세요');
    await opts.nth(1).click();
    await expect(opts.nth(1)).toHaveAttribute('aria-selected', 'true');
    await expect(go).toBeEnabled();
    const search = d.getByRole('textbox', { name: '작업 검색' });
    await search.focus();
    await page.keyboard.press('ArrowDown');
    await expect(opts.nth(2)).toHaveAttribute('aria-selected', 'true');
    await page.keyboard.press('Enter');
    await expect(d).toHaveCount(0);
    await expect(page.getByTestId('picked')).toHaveText('sb_b:B 병원 로비 안내 시스템');
  });
});
