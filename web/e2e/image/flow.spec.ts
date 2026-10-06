/**
 * 기본 흐름(§3.1) — IMG0 → IMG1 → IMG2 → IMG3G → IMG3 → IMG4. AC 1 · 2 · 3 · 29 · 30 · 31 · 49(파일명 규칙) · 50(다운로드).
 */
import { expect, test } from '@playwright/test';
import { api, DESC, shot } from './helpers';

test('IMG1 → IMG2 → 생성 → IMG3 → IMG4 기본 흐름', async ({ page, request }) => {
  test.setTimeout(150_000);
  await page.goto('/image');
  await expect(page.getByTestId('img0')).toBeVisible();
  await shot(page, 'IMG0');
  await page.getByRole('link', { name: '새 이미지 만들기' }).first().click();
  await expect(page).toHaveURL(/\/image\/new$/);

  // AC1 — 공간 선택 · placeholder · 설명 없으면 비활성
  await expect(page.getByRole('radio', { name: /공간/ })).toHaveAttribute('aria-checked', 'true');
  const ta = page.getByLabel('장면 설명');
  await expect(ta).toHaveAttribute('placeholder', '예) 카페 카운터 위에 3연 메뉴보드가 걸린 장면, 낮 시간, 손님 2~3명');
  const next = page.getByRole('button', { name: '상세 조건 입력' });
  await expect(next).toBeDisabled();
  await ta.fill(DESC);
  await expect(next).toBeEnabled();
  await shot(page, 'IMG1');
  await next.click();

  // AC2 — prefill: 칩 · 기본 조건 · 주 버튼
  await expect(page).toHaveURL(/\/image\/w\/imw_[^/]+\/conditions$/, { timeout: 15_000 });
  await expect(page.getByTestId('img-echo')).toHaveText(`공간 · ${DESC}`);
  await expect(page.getByTestId('img-prodchip')).toHaveText(/Smart Signage QM55C\s*×3/);
  for (const name of ['실사 렌더', '16:9', '4장']) await expect(page.getByRole('button', { name, exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: /이미지 4장 생성/ })).toBeVisible();
  await shot(page, 'IMG2');

  // AC3 — 2장 → 문구 · 시안 2개
  await page.getByRole('button', { name: '2장', exact: true }).click();
  const gen = page.getByRole('button', { name: /이미지 2장 생성/ });
  await expect(gen).toBeVisible();
  await gen.click();
  await expect(page).toHaveURL(/\/run\/ign_/);
  await expect(page.getByTestId('img3g-shots').locator('[data-testid^="shot-"]')).toHaveCount(2);
  await expect(page.getByText('제품 외형 맞춤')).toBeVisible();
  await shot(page, 'IMG3G');
  const result = page.getByRole('button', { name: '결과 보기' });
  await expect(result).toBeEnabled({ timeout: 90_000 });
  await shot(page, 'IMG3G-done');
  await result.click();

  // AC29 — 시안 1 선택 · 라벨 · 카드 머리
  await expect(page.getByTestId('img3-head')).toHaveText('시안 1 선택됨 · 3 / 3');
  await expect(page.getByText('시안 1 · 16:9 · 실사')).toBeVisible();
  await expect(page.getByText('선택됨', { exact: true })).toBeVisible();
  await shot(page, 'IMG3');

  // AC30 — 밝기 올리기(동기 보정 → 새 버전)
  await page.getByRole('button', { name: '밝기 올리기' }).click();
  await expect(page.getByTestId('img3-msg')).toContainText('밝기를 올린 보정 1 버전을 만들었어요');

  // 시안 2 고르기 → 선택 이동
  await page.getByRole('button', { name: '시안 2 선택' }).click();
  await expect(page.getByTestId('img3-head')).toHaveText('시안 2 선택됨 · 3 / 3');
  await page.getByRole('button', { name: '시안 1 선택' }).click();

  // IMG4 — 들어오면 저장 · 제목(보정본 v2) · 파일명 규칙 · PNG 다운로드 · 3840×2160
  await page.getByRole('button', { name: /제안서에 넣기/ }).click();
  await expect(page).toHaveURL(/\/export\/img_/);
  await expect(page.getByTestId('img4-title')).toHaveText('시안 1 · 보정본 v2');
  await expect(page.getByTestId('img-w')).toContainText('시안 1 보정본을 내보냅니다.');
  await expect(page.getByTestId('img4-fname')).toHaveValue(/^메뉴보드_시안1_v2\.png$/);
  await expect(page.getByRole('button', { name: '3840×2160' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('img4-saved')).toBeVisible();
  await shot(page, 'IMG4');
  // 한글 파일명은 이 환경 Chromium 이 저장 이름을 못 만든다 → 영문 파일명(칩)으로 내려받아 이름까지 본다
  await page.getByRole('button', { name: '영문 파일명' }).click();
  await expect(page.getByTestId('img4-fname')).toHaveValue('MenuBoard_Draft1_v2.png');
  const dl = page.waitForEvent('download');
  await page.getByRole('button', { name: 'PNG 다운로드' }).click();
  const file = await dl;
  expect(file.url()).toContain('download=1');
  expect(file.suggestedFilename()).toBe('MenuBoard_Draft1_v2.png');
  await expect(page.getByTestId('img4-msg')).toContainText('내려받았어요');
  // JPG 로 바꾸면 확장자만
  await page.getByRole('radio', { name: /JPG/ }).click();
  await expect(page.getByTestId('img4-fname')).toHaveValue('MenuBoard_Draft1_v2.jpg');
  await expect(page.getByRole('button', { name: 'JPG 다운로드' })).toBeVisible();

  // AC31 — 저장 → 갤러리에 보인다(공유 데이터라 개수 대신 그 타일)
  const workId = /\/image\/w\/(imw_[^/]+)/.exec(page.url())![1];
  const imgs = await api(request, 'GET', `/images?work_id=${workId}`);
  expect(imgs.items.some((t: { saved: boolean }) => t.saved)).toBeTruthy();
  await page.getByRole('link', { name: '갤러리 보기' }).click();
  await expect(page).toHaveURL(/\/image$/);
  await expect(page.getByTestId('img0-gallery')).toBeVisible();
});
