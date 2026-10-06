/**
 * IMG3E 부분 수정 — 사각 영역 → 지시문 → 적용 → 「적용됨 · 비교 중」 · 전/후 라벨 · 수정 기록 · 되돌리기(AC32 화면 · 36) ·
 * 사람 지우기 칩(IMG3 → IMG3E, 영역 자동) · 객체 선택(감지 상자).
 */
import { expect, test } from '@playwright/test';
import { api, doneWork, shot } from './helpers';

test('사각 영역 → 적용 → 비교 → 되돌리기', async ({ page, request }) => {
  test.setTimeout(150_000);
  const { work, run } = await doneWork(request, { count: 2 });
  const imageId = run.shots[0].image_id;
  await page.goto(`/image/w/${work.id}/edit/${imageId}`);
  await expect(page.getByTestId('img3e')).toBeVisible();
  await expect(page.getByTestId('img-echo')).toHaveText('부분 수정 · 시안 1');
  await expect(page.getByRole('button', { name: '사각형' })).toHaveAttribute('aria-pressed', 'true');
  const canvas = page.getByTestId('img3e-canvas');
  const b = (await canvas.boundingBox())!;
  await page.mouse.move(b.x + b.width * 0.4, b.y + b.height * 0.15);
  await page.mouse.down();
  await page.mouse.move(b.x + b.width * 0.5, b.y + b.height * 0.25, { steps: 4 });
  await page.mouse.move(b.x + b.width * 0.62, b.y + b.height * 0.42, { steps: 4 });
  await page.mouse.up();
  const region = page.getByTestId('img3e-region');
  await expect(region).toHaveCount(1, { timeout: 15_000 });
  await expect(region).toHaveAttribute('data-status', 'pending');
  await expect(region).toContainText('대기 · 적용 전');
  await expect(page.getByTestId('img3e-head')).toHaveText('영역 1 지시문 · 부분 수정');
  await region.getByLabel('영역 1 지시문').fill('계절 음료 사진 3장으로 바꾸고 글자는 빼줘');
  await shot(page, 'IMG3E-region');
  await region.getByRole('button', { name: '적용', exact: true }).click();
  await expect(region).toHaveAttribute('data-status', 'applied', { timeout: 60_000 });
  await expect(region).toContainText('적용됨 · 비교 중');
  await expect(page.getByTestId('img-w')).toContainText('영역 1을 먼저 고쳤으니 가운데 손잡이를 끌어 전/후를 비교해 보세요.');
  await expect(page.getByTestId('img3e-before')).toHaveText('전 · 원본');
  await expect(page.getByTestId('img3e-after')).toHaveText('후 · 수정 1');
  await expect(page.getByRole('slider', { name: '전/후 비교 손잡이' })).toBeVisible();
  await expect(page.getByTestId('img3e-history').getByRole('button', { name: /수정 1 · 영역 1/ })).toHaveAttribute('aria-pressed', 'true');
  await shot(page, 'IMG3E-compare');
  // 손잡이 키보드로
  await page.getByRole('slider', { name: '전/후 비교 손잡이' }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('slider', { name: '전/후 비교 손잡이' })).toHaveAttribute('aria-valuenow', '55');

  // AC36 — 되돌리기: 현재 = 원본, 수정 1 은 기록에 남는다
  await region.getByRole('button', { name: '되돌리기' }).click();
  await expect(region).toHaveAttribute('data-status', 'reverted', { timeout: 15_000 });
  const img = await api(request, 'GET', `/images/${imageId}`);
  expect(img.current.label).toBe('원본');
  expect(img.versions.map((v: { label: string }) => v.label)).toEqual(['원본', '수정 1 · 영역 1']);
  await expect(page.getByTestId('img3e-history').getByRole('button', { name: /원본/ })).toHaveAttribute('aria-pressed', 'true');

  // 저장하고 내보내기 → IMG4
  await page.getByRole('button', { name: /저장하고 내보내기/ }).click();
  await expect(page).toHaveURL(new RegExp(`/export/${imageId}`));
});

test('IMG3 「사람 제거」 → 사람 영역 자동 · 객체 선택 상자', async ({ page, request }) => {
  test.setTimeout(120_000);
  const { work, run } = await doneWork(request, { count: 2 });
  const imageId = run.shots[0].image_id;
  await page.goto(`/image/w/${work.id}/result`);
  await page.getByRole('button', { name: '사람 제거' }).click();
  await expect(page).toHaveURL(new RegExp(`/edit/${imageId}`));
  await expect(page.getByTestId('img-echo')).toHaveText('부분 수정 · 시안 1에서 사람 제거');
  const region = page.getByTestId('img3e-region');
  await expect(region).toHaveCount(1, { timeout: 15_000 });
  await expect(region.getByLabel('영역 1 지시문')).toHaveValue('사람을 지우고 배경을 자연스럽게 채워줘');
  // 객체 선택 — 감지 상자를 눌러 영역 추가
  await page.getByRole('button', { name: '객체 선택' }).click();
  const det = page.getByRole('button', { name: '가운데 메뉴보드 화면 선택' });
  await expect(det).toBeVisible({ timeout: 15_000 });
  await shot(page, 'IMG3E-object');
  await det.click();
  await expect(region).toHaveCount(2);
});
