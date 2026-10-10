/**
 * Storyboard 목록 · 정의서 새 버전 반영 e2e(02-storyboard §9.2 1 · 16) — 실제 백엔드.
 * 상태가 다른 스토리보드는 API 로 만든다(공유 데이터라 목록이 비어 있다고 가정하지 않고 id 로 행을 찾는다).
 */
import { expect, test, type Page } from '@playwright/test';
import { backendDown, getSb, saveNewRequirementVersion, seedRequirement, shot, storyboardAt, waitSb } from './fixtures';

test.describe.configure({ retries: 1 });
test.setTimeout(120_000);

test.beforeAll(async ({ request }) => {
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
});

const row = (page: Page, id: string) => page.getByRole('row').filter({ has: page.locator(`a[href*="${id}"]`) });

test('SB0 목록 — 탭 숫자 · 단계 알약 · 이어서 · 보기 · 열기(§9.2-1)', async ({ page, request }) => {
  const rq = await seedRequirement(request, { customer: 'F 시행사', project: '동탄 시니어 복합단지' });
  const going = await storyboardAt(request, rq, 'direction');
  const done = await storyboardAt(request, rq, 'saved');
  const writing = await storyboardAt(request, rq, 'direction');
  const r = await request.post(`/api/storyboard/v1/storyboards/${writing.id}/outline`, { data: {} });
  expect(r.status()).toBe(202);

  await page.goto('/storyboard/legacy');   // /storyboard 는 새 흐름 SB0(허브 목록)
  await expect(page.getByRole('heading', { name: '전략 수립 Storyboard' })).toBeVisible();
  const tabs = page.getByRole('tablist', { name: '상태' });
  await expect(tabs.getByRole('tab', { name: /^전체\s*\d+$/ })).toBeVisible();
  await expect(tabs.getByRole('tab', { name: /^진행 중\s*\d+$/ })).toBeVisible();
  await expect(tabs.getByRole('tab', { name: /^완료\s*\d+$/ })).toBeVisible();
  // 목차 잡이 도는 행은 `보기`
  await expect(row(page, writing.id).getByRole('link', { name: '보기' })).toBeVisible({ timeout: 10_000 });
  await expect(row(page, writing.id)).toContainText(/3\/5 목차 · 서사|목차 쓰는 중/);
  await expect(row(page, going.id)).toContainText('2/5 기획 방향');
  await expect(row(page, going.id)).toContainText('기획 방향을 고르는 중');
  await expect(row(page, going.id).getByRole('link', { name: '이어서' })).toBeVisible();
  await expect(row(page, done.id)).toContainText('완료');
  await expect(row(page, done.id).getByRole('link', { name: '열기' })).toBeVisible();
  await shot(page, 'SB0');
  await tabs.getByRole('tab', { name: /^완료/ }).click();
  await expect(page).toHaveURL(/\?tab=done$/);
  await expect(row(page, done.id)).toBeVisible();
  await expect(row(page, going.id)).toHaveCount(0);
  await tabs.getByRole('tab', { name: /^진행 중/ }).click();
  await expect(row(page, going.id)).toBeVisible();
  await expect(row(page, done.id)).toHaveCount(0);
  // 목차가 끝나면 그 행은 `이어서`
  await waitSb(request, writing.id, (s) => s.outline?.ready && !s.active_job, 40_000);
  await page.reload();
  await expect(row(page, writing.id).getByRole('link', { name: '이어서' })).toBeVisible();
});

test('정의서 v2 — 미리 보기(되돌리기 없음 · 뒤로) · SB3 띠 반영하기 → SB3V 원인 · 되돌리기(§9.2-16)', async ({ page, request }) => {
  const rq = await seedRequirement(request);
  const sb = await storyboardAt(request, rq, 'saved');
  await saveNewRequirementVersion(request, rq, '11/11 회의 반영');

  // RQ7B `미리 보기` → SB3V 미리 보기 모드(dry-run, 작업본 그대로)
  await page.goto(`/storyboard/${sb.id}/versions?preview_rq=${rq}`);
  await expect(page.locator('.sb-eyebrow').first()).toHaveText('목차 · 버전 · 미리 보기');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^v1 → 반영 후, 바뀐 곳 \d+$/, { timeout: 30_000 });
  await expect(page.getByText('요구사항 정의서 답변을 반영하면 이렇게 바뀌어요.')).toBeVisible();
  await expect(page.getByRole('button', { name: '되돌리기' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '뒤로' })).toBeVisible();
  await shot(page, 'SB3V-preview');
  const before = await getSb(request, sb.id);
  expect(before.requirement_ref.version).toBe(1);

  // 반영 요청 없이 저장된 새 버전 → SB3 띠(Q-18) `반영하기` → SB3V
  await page.goto(`/storyboard/${sb.id}/outline`);
  await expect(async () => {
    await page.reload();
    await expect(page.getByTestId('rq-update-band')).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 40_000, intervals: [2_000, 4_000] });
  await expect(page.getByTestId('rq-update-band')).toContainText('요구사항 정의서 v2가 새로 저장됐어요');
  await page.getByRole('button', { name: '반영하기' }).click();
  await expect(page).toHaveURL(`/storyboard/${sb.id}/versions`);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/^v1 → v2, 바뀐 곳 \d+$/, { timeout: 30_000 });
  await expect(page.locator('.sb-sub').first()).toContainText('요구사항 정의서 v2');
  await expect(page.getByTestId('change-row').getByRole('button', { name: '되돌리기' }).first()).toBeVisible();
  await shot(page, 'SB3V-rq-sync');
  const after = await getSb(request, sb.id);
  expect(after.requirement_ref.version).toBe(2);
});
