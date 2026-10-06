/**
 * IMG3V 변형 · 비율 · 해상도 — AC 38(변형 A~D 라벨) · 40(업스케일별 크기 · ×4 비활성) · 41(16:9 + 9:16 → 새 시안 2장).
 */
import { expect, test } from '@playwright/test';
import { api, doneWork, shot, waitRun } from './helpers';

test('이 시안으로 변형 4장 → 비율 2개로 만들기', async ({ page, request }) => {
  test.setTimeout(180_000);
  const { work, run } = await doneWork(request, { count: 2 });
  const base = run.shots[0].image_id;
  await page.goto(`/image/w/${work.id}/result`);
  await page.getByRole('button', { name: '이 시안으로 변형 4장' }).click();
  await expect(page).toHaveURL(new RegExp(`/variants/${base}`));
  await expect(page.getByTestId('img-echo')).toHaveText('변형 · 시안 1로 변형 4장');
  const vars = page.getByTestId('img3v-vars');
  // AC38 — LLM 목 라벨
  for (const l of ['A · 오후 자연광', 'B · 저녁 조명', 'C · 측면 시점', 'D · 메뉴보드 근접']) {
    await expect(vars.getByRole('button', { name: new RegExp(`변형 ${l[0]}`) }).locator('.img-var__tag')).toHaveText(l, { timeout: 90_000 });
  }
  await expect(page.getByTestId('img-w')).toContainText('시안 1을 기준으로 변형 4장을 만들었습니다.');
  await expect(vars.getByRole('button', { name: '변형 A 선택됨' })).toBeVisible();

  // AC40 — ×2 크기 · 원본 크기 · ×4 비활성
  const ratios = page.getByTestId('img3v-ratios');
  const px = { '16:9': ['3840×2160', '1920×1080'], '4:3': ['2880×2160', '1440×1080'], '1:1': ['2160×2160', '1080×1080'], '9:16': ['2160×3840', '1080×1920'] };
  for (const [a, [x2]] of Object.entries(px)) await expect(ratios.getByRole('button', { name: `${a} ${x2}` })).toBeVisible();
  await page.getByRole('button', { name: '원본', exact: true }).click();
  for (const [a, [, x1]] of Object.entries(px)) await expect(ratios.getByRole('button', { name: `${a} ${x1}` })).toBeVisible();
  await expect(page.getByTestId('img3v-head')).toHaveText('변형 A 선택됨 · 16:9 · 업스케일 없음');
  await page.getByRole('button', { name: '×2', exact: true }).click();
  const x4 = page.getByRole('button', { name: '×4', exact: true });
  await expect(x4).toBeDisabled();
  await expect(x4).toHaveAttribute('title', '×4는 업스케일 모델이 있어야 해요');

  // AC41 — 16:9 + 9:16, 다시 구성, ×2
  await ratios.getByRole('button', { name: '9:16 2160×3840' }).click();
  await expect(ratios.getByRole('button', { name: '9:16 2160×3840' })).toContainText('위아래는 새로 채움');
  await expect(page.getByTestId('img3v-head')).toHaveText('변형 A 선택됨 · 16:9 + 9:16 · ×2 업스케일');
  await shot(page, 'IMG3V');
  await page.getByRole('button', { name: '2개 비율로 만들기' }).click();
  await expect(page).toHaveURL(/\/run\/ign_/);
  await expect(page.getByTestId('img-w')).toContainText('2개 비율을 만들고 있어요');
  const runId = /\/run\/(ign_[^/?]+)/.exec(page.url())![1];
  const r = await waitRun(request, runId);
  expect(r.status).toBe('succeeded');
  const sizes = await Promise.all(r.shots.map(async (s: { image_id: string }) => {
    const d = await api(request, 'GET', `/images/${s.image_id}`);
    return [d.aspect, d.base_image_id !== null];
  }));
  expect(sizes).toEqual([['16:9', true], ['9:16', true]]);
  await page.getByRole('button', { name: '결과 보기' }).click();
  await expect(page).toHaveURL(new RegExp(`run=${runId}`));
  await expect(page.getByTestId('img3-shots').locator('[data-state="done"]')).toHaveCount(2);
  await shot(page, 'IMG3-renditions');
});
