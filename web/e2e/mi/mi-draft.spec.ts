/**
 * MI 저장 전 초안(보드에 없음 · 2026-10-10) — 실제 스택(MODEL_MODE=mock · mocks/ai-tools/mi.flow_analyze.v1).
 * 「‹ Storyboard」 → Gate → 다시 시작하면 같은 초안을 이어서 연다(분석을 다시 돌리지 않음 · `POST /v1/mi-flows` 200) →
 * 목록(보드 List)의 초안 줄에 손을 올리면 × → 확인 → 지운다(`DELETE /v1/mi-flows/{id}` 204).
 * 실행: WM_E2E_SUITE=mi WM_E2E_DEV=1 WM_E2E_PORT=5203 npx playwright test e2e/mi/mi-draft.spec.ts --workers=1
 */
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { shot } from './helpers';

const draftsOf = async (request: APIRequestContext, sbId: string) =>
  ((await (await request.get('/api/mi/v1/mi-flows?limit=200')).json()).items as Array<{ id: string; sb_id: string }>).filter((d) => d.sb_id === sbId);

/** 목록의 초안 줄 — 손을 올려야 × 가 보이고, 확인창에서 「지우기」를 누르면 줄이 빠진다 */
async function deleteDraftRow(page: Page, title: string, name?: string) {
  const row = page.locator('.fl-tr').filter({ hasText: title });
  await expect(row).toHaveCount(1);
  await expect(row).toContainText('작성 중');
  const x = row.getByRole('button', { name: `${title} 지우기` });
  await page.mouse.move(5, 5);
  await expect(x).toHaveCSS('opacity', '0');
  await row.hover();
  await expect(x).toHaveCSS('opacity', '1');
  await x.click();
  const dlg = page.getByRole('dialog', { name: '작성 중인 초안을 지울까요?' });
  await expect(dlg).toContainText(`‘${title}’ 초안을 지워요. 저장하지 않은 내용이라 되돌릴 수 없어요.`);
  if (name) await shot(page, name);
  await dlg.getByRole('button', { name: '지우기', exact: true }).click();
  await expect(dlg).toHaveCount(0);
  await expect(page.getByText('초안을 지웠어요')).toBeVisible();
  await expect(row).toHaveCount(0);
}

test('MI 초안 — 「‹ Storyboard」 → Gate → 다시 시작해도 같은 초안 · 목록에서 × 로 지우기', async ({ page, request }) => {
  test.setTimeout(150_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makeStoryboard(request, { dss: true, name: `용산 초안 ${tag()}` });
  const title = `${sb.name} 시장 분석`;

  // Gate → 시작 → 분석 로딩 → MI2
  await page.goto('/mi/new');
  const mine = page.getByRole('radio', { name: new RegExp(sb.name) });
  await mine.click();
  await page.getByRole('button', { name: /이 Storyboard로 시작/ }).click();
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}$/);
  const id = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  const doc = await (await request.get(`/api/mi/v1/mi-flows/${id}`)).json();
  const jobs = doc.progress.job_id as string;

  // 「‹ Storyboard」 → Gate(이 Storyboard 가 골라져 있음 · 저장 전 초안이 있어 「작성 중 초안 있음」) → 「초안 이어 쓰기」 → 같은 초안 · 분석을 다시 돌리지 않음
  await page.locator('.mif-foot .wm-flow__back').click();
  await expect(page).toHaveURL(new RegExp(`/mi/new\\?sb=${sb.id}$`));
  const again = page.getByRole('radio', { name: new RegExp(sb.name) });
  await expect(again).toHaveAttribute('aria-checked', 'true');
  await expect(again).toContainText('작성 중 초안 있음');
  await expect(page.locator('.fl-footline')).toContainText(`작성 중이던 ${doc.code} 초안을 이어서 열어요`);
  await page.getByRole('button', { name: /초안 이어 쓰기/ }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${id}$`));
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible();
  expect((await draftsOf(request, sb.id)).map((d) => d.id)).toEqual([id]);
  expect((await (await request.get(`/api/mi/v1/mi-flows/${id}`)).json()).progress.job_id).toBe(jobs);   // 새 분석 잡 없음

  // 목록 → 초안 줄 × → 확인 → 빠짐(서버에서도 지워짐)
  await page.goto('/mi');
  await expect(page.getByRole('heading', { level: 1, name: 'Market Intelligence' })).toBeVisible();
  await deleteDraftRow(page, title, 'MI0-draft-delete');
  expect((await request.get(`/api/mi/v1/mi-flows/${id}`)).status()).toBe(404);
  await page.reload();
  await expect(page.getByRole('heading', { level: 1, name: 'Market Intelligence' })).toBeVisible();
  await expect(page.locator('.fl-tr').filter({ hasText: title })).toHaveCount(0);
  expect(await draftsOf(request, sb.id)).toEqual([]);
});
