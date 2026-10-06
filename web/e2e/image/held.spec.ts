/**
 * IMG3X 생성 실패 · 제한 안내 — AC 20(보류 · 사유 상태 · 머리) · 21(대안으로 이어서) · 22(보류 건너뛰기) · 24(다른 대안 입력) · 25(자동 대안만이면 IMG3 띠).
 */
import { expect, test } from '@playwright/test';
import { api, newWork, shot, waitRun } from './helpers';

const HELD_DESC = '경쟁사 A 메뉴보드 옆에 QM55C, 배우 ○○○가 주문하는 장면';

async function heldRun(request: Parameters<typeof api>[0]) {
  const w = await newWork(request, { kind: 'space', description: HELD_DESC });
  await api(request, 'POST', `/works/${w.id}:prefill`);
  const acc = await api(request, 'POST', `/works/${w.id}/runs`, { kind: 'initial', count: 4, notify: false });
  const run = await waitRun(request, acc.run_id, ['awaiting_input', 'succeeded', 'failed']);
  expect(run.status).toBe('awaiting_input');
  return { w, runId: acc.run_id as string };
}

test('보류 2장 · 사유 상태 · 다른 대안 · 대안으로 이어서 생성(AC20 · 21 · 24)', async ({ page, request }) => {
  test.setTimeout(150_000);
  const { w, runId } = await heldRun(request);
  await page.goto(`/image/w/${w.id}/run/${runId}`);
  await expect(page.getByTestId('img3x')).toBeVisible();
  await expect(page.getByTestId('img-w')).toHaveText('4장 중 2장을 만들고 2장은 보류했어요. 요청에 그대로 만들 수 없는 부분이 2가지 있습니다. 항목마다 대안을 고르면 보류한 2장을 이어서 만듭니다.');
  await expect(page.getByTestId('img3x-head')).toHaveText('보류 사유 2 · 대안 1개 선택됨');
  await expect(page.getByTestId('img3x-foot-head')).toHaveText('대안 선택 · 2개 중 1개 선택됨');
  const issues = page.getByTestId('img3x-issue');
  await expect(issues.filter({ hasText: '경쟁사 A 로고 · 제품은 이미지에 넣지 않아요' }).getByTestId('img3x-state')).toHaveText('대안 선택됨');
  const person = issues.filter({ hasText: '실존 인물' });
  await expect(person.getByTestId('img3x-state')).toHaveText('선택 필요');
  await expect(person.getByRole('button', { name: '인물 없이 · 기본값' })).toHaveClass(/img-pill--def/);
  await expect(issues.filter({ hasText: '경쟁사 A' }).getByRole('link', { name: /Why Samsung 비교표로 보내기/ })).toHaveAttribute('href', /focus=CM/);
  await expect(page.getByTestId('img3x-strip').locator('.img-strip__held')).toHaveCount(2);
  await shot(page, 'IMG3X');

  // AC24 — 다른 대안(정책 재검사 통과 시에만)
  await page.getByLabel('다른 대안 입력').fill('경쟁사 화면은 회색 박스로');
  await page.getByRole('button', { name: '보내기' }).click();
  await expect(page.getByTestId('img3x-note')).toBeVisible();
  // 생성 이미지 사용 기준 팝오버
  await page.getByRole('button', { name: '생성 이미지 사용 기준' }).click();
  await expect(page.getByRole('dialog', { name: '생성 이미지 사용 기준' })).toContainText('실존 인물');
  await page.getByRole('dialog', { name: '생성 이미지 사용 기준' }).getByRole('button', { name: '닫기' }).click();

  // 인물 대안 고르기 → 2개 중 2개
  await person.getByRole('button', { name: '가상 인물로' }).click();
  await expect(page.getByTestId('img3x-foot-head')).toHaveText('대안 선택 · 2개 중 2개 선택됨');
  await page.getByRole('button', { name: /대안으로 2장 이어서 생성/ }).click();
  await expect(page.getByTestId('img3g')).toBeVisible({ timeout: 15_000 });
  const run = await waitRun(request, runId);
  expect([run.status, run.done]).toEqual(['succeeded', 4]);
  await expect(page.getByRole('button', { name: '결과 보기' })).toBeEnabled({ timeout: 15_000 });
  await page.getByRole('button', { name: '결과 보기' }).click();
  await expect(page.getByTestId('img3-shots').locator('[data-state="done"]')).toHaveCount(4);
  await expect(page.getByTestId('shot-3')).toBeVisible();
});

test('보류 2장 건너뛰기 → 2장으로 끝(AC22)', async ({ page, request }) => {
  test.setTimeout(120_000);
  const { w, runId } = await heldRun(request);
  await page.goto(`/image/w/${w.id}/run/${runId}`);
  await page.getByRole('button', { name: '보류 2장 건너뛰기' }).click();
  const run = await waitRun(request, runId, ['succeeded', 'failed', 'canceled']);
  expect(run.status).toBe('succeeded');
  expect(run.shots.filter((s: { state: string }) => s.state === 'canceled')).toHaveLength(2);
  await expect(page.getByRole('button', { name: '결과 보기' })).toBeEnabled({ timeout: 15_000 });
  await page.getByRole('button', { name: '결과 보기' }).click();
  await expect(page.getByTestId('img3-shots').locator('[data-state="done"]')).toHaveCount(2);
});

test('자동 대안만 있으면 보류 없이 만들고 IMG3 에 바꾼 내용 띠(AC25)', async ({ page, request }) => {
  test.setTimeout(120_000);
  const w = await newWork(request, { kind: 'space', description: '경쟁사 A 메뉴보드 옆에 QM55C 가 걸린 카페 카운터' });
  await api(request, 'POST', `/works/${w.id}:prefill`);
  const acc = await api(request, 'POST', `/works/${w.id}/runs`, { kind: 'initial', count: 2, notify: false });
  const run = await waitRun(request, acc.run_id);
  expect([run.status, run.held]).toEqual(['succeeded', 0]);
  await page.goto(`/image/w/${w.id}/result`);
  await expect(page.getByTestId('img3-change')).toContainText('요청 중 1가지를 바꿔서 만들었어요');
  await page.getByTestId('img3-change').getByRole('button', { name: '자세히' }).click();
  await expect(page.getByText(/경쟁사 A 로고 · 제품은 이미지에 넣지 않아요 → 로고 없는 일반 화면으로/)).toBeVisible();
  await shot(page, 'IMG3-change-note');
});
