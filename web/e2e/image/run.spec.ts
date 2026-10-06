/**
 * IMG3G 생성 중 · 대기열 · 취소 · IMG0 진행 표시 — AC 13(대기 카드 문구) · 14(이 장 취소) · 15(전체 취소 · 조건 수정) · 16(대기열) · 18(떠나도 진행).
 * 개발 서버는 IMAGE_DEV_SHOT_DELAY_S(예 2.5초)로 시안마다 늦춰 둔 상태여야 진행 중 화면이 보인다.
 */
import { expect, test } from '@playwright/test';
import { api, DESC, newWork, shot, waitRun } from './helpers';

async function startRun(request: Parameters<typeof api>[0], count: 2 | 4 = 4) {
  const w = await newWork(request, { kind: 'space', description: DESC });
  await api(request, 'POST', `/works/${w.id}:prefill`);
  const acc = await api(request, 'POST', `/works/${w.id}/runs`, { kind: 'initial', count, notify: true });
  return { w, runId: acc.run_id as string };
}

test('대기 카드 문구 · 이 장 취소 · 끝나면 결과 보기(AC13 · 14)', async ({ page, request }) => {
  test.setTimeout(120_000);
  const { w, runId } = await startRun(request, 4);
  await page.goto(`/image/w/${w.id}/run/${runId}`);
  const shots = page.getByTestId('img3g-shots');
  // 동시 2장 → 시안 3 · 4 는 대기, 문구는 먼저 시작한 시안
  const waiting = shots.locator('[data-state="waiting"]');
  await expect(waiting.first()).toContainText(/시안 \d+[이가] 끝나면 시작해요/, { timeout: 20_000 });
  expect(await shots.locator('[data-state="composing"], [data-state="rendering"], [data-state="qc"]').count()).toBeLessThanOrEqual(2);
  await shot(page, 'IMG3G-waiting');
  // 시안 4 취소
  const s4 = page.getByTestId('shot-4');
  await s4.hover();
  await s4.getByRole('button', { name: '시안 4 이 장 취소' }).click();
  await expect(s4).toHaveAttribute('data-state', 'canceled');
  await expect(s4).toContainText('취소됨');
  const run = await waitRun(request, runId);
  expect([run.status, run.done, run.total]).toEqual(['succeeded', 3, 4]);
  await expect(page.getByRole('button', { name: '결과 보기' })).toBeEnabled({ timeout: 15_000 });
  await expect(page.getByTestId('img3g-head')).toHaveText('생성 완료 · 3 / 4 · 3 / 3');
});

test('목록에서 기다리기 — IMG0 배지 · 생성 중 타일(AC18) · 전체 취소 · 조건 수정(AC15)', async ({ page, request }) => {
  test.setTimeout(120_000);
  const { w, runId } = await startRun(request, 4);
  await page.goto(`/image/w/${w.id}/run/${runId}`);
  await page.getByRole('button', { name: '목록에서 기다리기' }).click();
  await expect(page).toHaveURL(/\/image$/);
  const row = page.locator(`a[data-testid="img0-work"][href*="${runId}"]`);
  await expect(row).toBeVisible({ timeout: 10_000 });
  await expect(row.locator('[data-badge="running"]')).toHaveText(/생성 중 \d \/ 4/);
  const tile = page.locator(`a[data-testid="img0-tile-gen"][href*="${runId}"]`);
  await expect(tile).toBeVisible();
  await expect(tile).toContainText('생성 중');
  await expect(tile).toContainText('진행 보기');
  await shot(page, 'IMG0-running');
  // 진행 보기 → 시안 1 이 끝나면 전체 취소 · 조건 수정
  await tile.click();
  await expect(page).toHaveURL(new RegExp(`/run/${runId}`));
  await expect(page.getByTestId('shot-1')).toHaveAttribute('data-state', 'done', { timeout: 30_000 });
  await page.getByRole('button', { name: '전체 취소 · 조건 수정' }).click();
  await expect(page).toHaveURL(new RegExp(`/image/w/${w.id}/conditions$`));
  await expect(page.getByTestId('img-prodchip')).toHaveText(/QM55C\s*×3/);
  const run = await waitRun(request, runId, ['canceled', 'succeeded']);
  expect(run.status).toBe('canceled');
  const mine = await api(request, 'GET', `/images?work_id=${w.id}`);
  expect(mine.items.filter((t: { saved: boolean; status: string }) => t.saved && t.status === 'done').length).toBeGreaterThanOrEqual(1);
});

test('내 대기열 — 두 번째 작업은 대기 중 · 다음 차례(AC16)', async ({ page, request }) => {
  test.setTimeout(150_000);
  const a = await startRun(request, 4);
  const b = await startRun(request, 2);
  await page.goto(`/image/w/${b.w.id}/run/${b.runId}`);
  await expect(page.getByTestId('img3g-head')).toHaveText(/^대기 중( · 앞에 \d+건)? · 3 \/ 3$/, { timeout: 15_000 });
  await shot(page, 'IMG3G-queued');
  await page.goto(`/image/w/${a.w.id}/run/${a.runId}`);
  const q = page.getByTestId('img3g-queue');
  await expect(q).toBeVisible({ timeout: 15_000 });
  await expect(q).toContainText('이 작업이 끝나면 순서대로 이어서 생성돼요');
  await expect(q.locator('.img-queue__row').filter({ hasText: '다음 차례' })).toHaveCount(1);
  await shot(page, 'IMG3G-queue');
  // b 는 a 가 끝나기 전에는 시작하지 않는다
  const ra = await api(request, 'GET', `/runs/${a.runId}`);
  const rb = await api(request, 'GET', `/runs/${b.runId}`);
  if (ra.status === 'running') expect(rb.status).toBe('queued');
  await waitRun(request, a.runId);
  await waitRun(request, b.runId);
});
