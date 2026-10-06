/**
 * 입력 방식(§3.2 「02 입력 방식」) — BE1 → BE1D(벡터 PDF) · BE1 → BE1P(현장 사진 3장) · 휴대폰(QR) 올리기.
 * AC 8 · 10 · 13 · 16 · 17 · 18(일부) · 19 · 20 · 21.
 */
import { expect, test } from '@playwright/test';
import { FIX, shot } from './helpers';

test('도면 PDF → BE1D 인식 확인 · 문 질문 · 말로 고치기 → BE2', async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto('/birdseye/new');
  await page.getByTestId('be1-file').setInputFiles(FIX('lobby_plan_1F.pdf'));
  await expect(page.getByTestId('be1-next')).toBeEnabled();
  await page.getByTestId('be1-next').click();

  await expect(page).toHaveURL(/\/birdseye\/be_[^/]+\/space\/plan\?plan=bep_/, { timeout: 20_000 });
  await expect(page.getByTestId('be1d-scale')).toHaveText('축척 1:100 감지 · 면적 396 ㎡ (약 120평)', { timeout: 30_000 });
  await expect(page.getByTestId('be1d-head')).toHaveText('5종 · 확인 2');
  const els = page.getByTestId('be1d-elements');
  for (const t of ['외벽 4면', '전면 유리창 2구간', '주출입구 1 · 뒤쪽 문 1', '2개 · 600 × 600 mm', 'EV · 계단 · 배치 제외']) await expect(els).toContainText(t);
  await expect(page.getByTestId('be1d-q-1')).toContainText('치수 보정 · 정면 폭');
  await expect(page.getByTestId('be1d-q-1').getByRole('radio', { name: '표기값 24.0 m' })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByTestId('be1d-q-2')).toContainText('뒤쪽 문은 어떤 문인가요?');
  await expect(page.getByTestId('be1d-canvas')).toBeVisible();
  await shot(page, 'BE1D');

  // 문 질문 → 벽으로 처리(AC13)
  await page.getByTestId('be1d-q-2').getByRole('button', { name: '벽으로 처리' }).click();
  await expect(els).not.toContainText('뒤쪽 문', { timeout: 10_000 });
  await expect(els).toContainText('주출입구 1');

  // 말로 고치기(AC16)
  await page.getByLabel('말로 고치기', { exact: true }).fill('오른쪽 기둥은 철거됐어');
  await page.getByLabel('말로 고치기', { exact: true }).press('Enter');
  await expect(els).toContainText('1개 · 600 × 600 mm', { timeout: 30_000 });

  await page.getByTestId('be1d-next').click();
  await expect(page).toHaveURL(/\/products$/, { timeout: 15_000 });
  await expect(page.getByTestId('be-w')).toContainText('공간을 파악했습니다', { timeout: 30_000 });
});

test('현장 사진 3장 → BE1P 역광 · 그대로 사용 · 사진에 없는 정보 · GIF 거절 · 휴대폰 올리기', async ({ page, browser }) => {
  test.setTimeout(150_000);
  await page.goto('/birdseye/new');
  await page.getByTestId('be1-chip-control_room').click();
  await page.getByLabel('공간 설명').fill('관제실 리뉴얼이에요. 정면 상황판 교체가 핵심이고 운영석은 2열입니다.');
  await page.getByTestId('be1-file').setInputFiles([FIX('wall_1.jpg'), FIX('wall_2.jpg'), FIX('window_backlit.jpg')]);
  await page.getByTestId('be1-next').click();

  await expect(page).toHaveURL(/\/birdseye\/be_[^/]+\/space\/photos$/, { timeout: 20_000 });
  await expect(page.getByTestId('be1p-head')).toContainText('인식 완료 2 · 확인 필요 1', { timeout: 40_000 });
  const bad = page.getByTestId('be1p-photo-3');
  await expect(bad).toContainText('역광 · 창 위치가 흐려요');
  await expect(bad.getByRole('button', { name: '다시 찍기' })).toBeVisible();
  await expect(page.getByTestId('be1p-dirs')).toContainText('3 / 4 · 천장 없음');
  await expect(page.getByTestId('be1p-ceiling')).toHaveText('없음 · 층고는 추정값');
  await expect(page.getByTestId('be-w')).toContainText('창 쪽 사진은 역광으로 창 위치가 흐리니 다시 찍어 주시고');
  await shot(page, 'BE1P');

  // 그대로 사용(AC17) → 기준 사진 수에 포함
  await bad.getByRole('button', { name: '그대로 사용' }).click();
  await expect(bad).toContainText('그대로 사용', { timeout: 10_000 });
  await expect(page.getByTestId('be1p-head')).toContainText('인식 완료 3 · 확인 필요 0');
  await expect(page.getByText('· 사진 3장 기준')).toBeVisible();

  // 사진에 없는 정보(AC19)
  await page.getByLabel('사진에 없는 정보', { exact: true }).fill('상황판 벽 폭 9m, 운영석 2열 12석');
  await page.getByLabel('사진에 없는 정보', { exact: true }).press('Enter');
  await expect(page.getByTestId('be1p-summary')).toContainText('상황판 벽 폭 9 m', { timeout: 20_000 });
  await expect(page.getByTestId('be1p-summary')).toContainText('운영석 2열 12석');

  // GIF 거절(AC21)
  await page.getByTestId('be1p-file').setInputFiles({ name: 'anim.gif', mimeType: 'image/gif', buffer: Buffer.from('GIF89a') });
  await expect(page.getByTestId('be1p-err')).toHaveText('JPG · PNG · HEIC만 올릴 수 있어요');

  // 휴대폰으로 올리기(AC20) — QR 토큰 → 모바일 화면에서 올리면 BE1P 에 카드가 붙는다
  await page.getByRole('button', { name: '휴대폰으로 올리기' }).click();
  const dlg = page.getByRole('dialog');
  await expect(dlg.getByRole('img', { name: '휴대폰 올리기 QR' })).toBeVisible();
  const text = (await dlg.textContent()) ?? '';
  const token = /\/m\/upload\/([A-Za-z0-9_-]+)/.exec(text)?.[1];
  expect(token, 'QR 주소에 토큰').toBeTruthy();
  await shot(page, 'BE1P-qr');
  await page.keyboard.press('Escape');

  const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'ko-KR', isMobile: true });
  const mp = await phone.newPage();
  await mp.goto(`/birdseye/m/${token}`);
  await expect(mp.getByTestId('be-mobile')).toContainText('현장 사진 올리기');
  await mp.locator('input[type=file]').setInputFiles(FIX('wall_2.jpg'));
  await expect(mp.getByText('wall_2.jpg · 올렸어요')).toBeVisible({ timeout: 20_000 });
  await shot(mp, 'BE1P-mobile');
  await phone.close();

  await expect(page.getByTestId('be1p-photo-4')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId('be1p-next')).toBeEnabled();
});
