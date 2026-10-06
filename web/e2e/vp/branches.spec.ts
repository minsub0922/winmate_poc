/**
 * 05-vp 갈래 — VP1Q 되묻기(메모뿐 · 결재자 모름) · VP1A 재료 확인 · VPR 규칙 시트 · VP0 복제 · VP3 한 문장 버전.
 */
import { test } from '@playwright/test';
import { archive, collectToStructure, expect, shot, startDirect, tag } from './helpers';

test.describe.configure({ mode: 'serial' });

test('VP1Q 되묻기 — RFP 없이 메모뿐이면 결재자를 확인 권장으로 묻고, 이대로 진행하면 VP2', async ({ page }) => {
  test.setTimeout(180_000);
  const id = await startDirect(page, `다온 빌딩 ${tag()}`, { rfp: false, note: '회의실 디스플레이 교체 문의' });
  await page.getByRole('button', { name: '가치 구조 만들기' }).click();
  await page.waitForURL(new RegExp(`/vp/${id}/questions$`), { timeout: 90_000 });
  const card = page.getByTestId('vp-q-approver');
  await expect(card).toContainText('누가 결재하나요?');
  await expect(card).toContainText('확인 권장');
  await expect(page.getByText(/^답이 없으면 .+로 진행하고, 결과에서 언제든 바꿀 수 있어요\.$/)).toBeVisible();
  await expect(page.getByLabel('자동으로 정한 것')).toBeVisible();
  await expect(page.locator('.vp-dock')).toContainText('선택 필요 0 · 확인 권장 1');
  // 두 명을 고르면 이해관계자형(VP-H) 안내가 굵어진다
  const picks = card.locator('.vp-pick');
  await picks.nth(0).click();
  if (!(await picks.nth(1).locator('input').isChecked())) await picks.nth(1).click();
  await expect(card.locator('.vp-q__hint--strong')).toBeVisible();
  await shot(page, 'VP1Q');
  await page.getByRole('button', { name: '이대로 진행' }).click();
  await page.waitForURL(/\/(structure|materials\/review)$/, { timeout: 90_000 });
  if (/review$/.test(page.url())) await page.getByRole('button', { name: '가치 구조로' }).click();
  await page.waitForURL(new RegExp(`/vp/${id}/structure$`), { timeout: 30_000 });
  await expect(page.getByText(/^메시지 구조 · /)).toBeVisible();
  await expect(page.locator('.vp-spine__card[data-role="VP"]')).toContainText('VP-H');
  await archive(page, id);
});

test('VP1A 재료 확인 · VPR 규칙 시트 · 업종 바꾸기', async ({ page }) => {
  test.setTimeout(180_000);
  const id = await startDirect(page, `한결 커피 ${tag()}`);
  // 업종을 직접 고르면 '고정'
  await page.getByRole('button', { name: '바꾸기' }).click();
  await page.getByRole('dialog', { name: '업종 고르기' }).getByText('외식 · 카페', { exact: true }).click();
  await expect(page.locator('.vp-ind')).toContainText('고정');
  await collectToStructure(page);

  await page.goto(`/vp/${id}/materials/review`);
  await expect(page.getByText('뽑은 재료')).toBeVisible();
  await expect(page.locator('.vp-mat').first()).toBeVisible();
  await shot(page, 'VP1A');

  // VPR — 판단 규칙(읽기 전용 시트)
  await page.goto(`/vp/${id}/structure`);
  await page.getByRole('link', { name: '판단 규칙' }).click();
  await page.waitForURL(/\/vp\/rules$/);
  const sheet = page.getByRole('dialog', { name: '에이전트 라우팅 규칙' });
  await expect(sheet).toContainText('구조와 레이아웃은 스스로 고르고, 다섯 경우만 묻습니다');
  await expect(sheet).toContainText('레이아웃 선택 — 시트마다');
  await expect(sheet).toContainText('사람에게 묻는 경우는 이 다섯뿐');
  await expect(sheet).toContainText('0 / 16');
  await shot(page, 'VPR');
  await page.keyboard.press('Escape');
  await page.waitForURL(new RegExp(`/vp/${id}/structure$`));
  await archive(page, id);
});

test('VP3 한 문장 버전 · VP4 메시지 복사 · VP0 복제(고정 시트 유지)', async ({ page, context }) => {
  test.setTimeout(300_000);
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const base = `누리 커피 ${tag()}`;
  const id = await startDirect(page, base);
  await collectToStructure(page);
  await page.getByRole('button', { name: /장 만들기/ }).click();
  await page.waitForURL(new RegExp(`/vp/${id}/result$`), { timeout: 180_000 });

  await page.getByRole('button', { name: '한 문장 버전도 만들기' }).click();
  await expect(page.getByLabel('변형 시트')).toContainText('VP-G', { timeout: 90_000 });

  // 가치 제안 시트를 고정
  await page.locator('.vp-dock').getByRole('link', { name: '레이아웃 바꾸기' }).click();
  await page.getByRole('checkbox', { name: /이 시트 고정/ }).check();
  await page.getByRole('button', { name: '고정 바꾸기' }).click();
  await page.waitForURL(new RegExp(`/vp/${id}/result$`), { timeout: 60_000 });
  await expect(page.locator('[data-testid="vp-sheet"][data-role="VP"]')).toContainText('고정');

  await page.goto(`/vp/${id}/export`);
  await page.getByRole('button', { name: /메시지 복사/ }).click();
  await expect(page.getByText('메시지를 복사했어요')).toBeVisible();

  // VP0 → 이전 가치 제안 복제
  await page.goto('/vp');
  await page.getByRole('button', { name: /이전 가치 제안 복제/ }).click();
  const dlg = page.getByRole('dialog', { name: '복제할 가치 제안 고르기' });
  await dlg.getByLabel('작업 검색').fill(base);
  await dlg.getByRole('option', { name: new RegExp(base) }).first().click();
  await dlg.getByPlaceholder('예: K 베이커리').fill(`${base} 베이커리`);
  await shot(page, 'VP0-clone');
  await dlg.getByRole('button', { name: '복제하기' }).click();
  await page.waitForURL(/\/vp\/vp_[^/]+\/structure$/, { timeout: 30_000 });
  const cloneId = page.url().match(/\/vp\/(vp_[^/]+)\//)![1];
  expect(cloneId).not.toBe(id);
  await expect(page.getByText('상속 · 고객명만 교체')).toBeVisible();
  await expect(page.locator('.vp-spine__card[data-role="VP"]')).toContainText('고정');
  await archive(page, cloneId);
  await archive(page, id);
});
