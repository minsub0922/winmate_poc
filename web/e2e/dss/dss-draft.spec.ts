/**
 * DSS 저장 전 초안(보드에 없음 · 2026-10-10) — 실제 스택(MODEL_MODE=mock).
 * Gate 를 다시 거쳐 같은 Storyboard 로 시작하면 같은 초안을 이어서 연다(새 초안이 늘지 않음 · `POST /v1/dss` 200) →
 * 목록(보드 List)의 초안 줄에 손을 올리면 × → 확인 → 지운다(`DELETE /v1/dss/{id}` 204) → 다시 시작하면 새 초안.
 * 실행: WM_E2E_SUITE=dss WM_E2E_DEV=1 WM_E2E_PORT=5211 npx playwright test e2e/dss/dss-draft.spec.ts --workers=1
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import { makeStoryboard, shotTo, tag } from '../shell/flowkit';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '__screens__');

/** Gate(보드 Gate) — 우리 Storyboard 를 골라 시작 → 편집 화면 id */
async function startFromGate(page: Page, name: string, resume = false) {
  await page.goto('/dss/new');
  const row = page.getByRole('radio', { name: new RegExp(name) });
  await row.click();
  await expect(row).toHaveAttribute('aria-checked', 'true');
  // 저장 전 초안은 허브에 없다(「있음」이 아님) — 초안이 있으면 줄에 「작성 중 초안 있음」 · 버튼 「초안 이어 쓰기」(GateScreen drafts)
  await expect(row).toContainText(resume ? '작성 중 초안 있음' : '이어서 만들기');
  if (resume) {
    await expect(page.locator('.fl-footline')).toContainText('초안을 이어서 열어요');
    await shotTo(page, DIR, 'DS1-draft-new');
  }
  await page.getByRole('button', { name: resume ? '초안 이어 쓰기' : '이 Storyboard로 시작' }).click();
  await expect(page).toHaveURL(/\/dss\/dss_[0-9A-Za-z]+$/, { timeout: 15_000 });
  await expect(page.getByRole('heading', { name: '공간과 제품을 정해요' })).toBeVisible();
  return page.url().split('/').pop()!.split('?')[0];
}

const draftsOf = async (request: APIRequestContext, sbId: string) =>
  ((await (await request.get('/api/dss/v1/dss?limit=200')).json()).items as Array<{ id: string; sb_id: string | null }>).filter((d) => d.sb_id === sbId);

/** 목록의 초안 줄 — 손을 올려야 × 가 보이고, 확인창에서 「지우기」를 누르면 줄이 빠진다 */
async function deleteDraftRow(page: Page, title: string, shot?: string) {
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
  if (shot) await shotTo(page, DIR, shot);
  await dlg.getByRole('button', { name: '지우기', exact: true }).click();
  await expect(dlg).toHaveCount(0);
  await expect(page.getByText('초안을 지웠어요')).toBeVisible();
  await expect(row).toHaveCount(0);
}

test('DSS 초안 — Gate 를 다시 거쳐도 같은 초안 · 목록에서 × 로 지우기 · 지운 뒤 새 초안', async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `판교 초안 ${tag()}`;
  const sb = await makeStoryboard(request, { name });

  // 처음 시작 → 공간 하나 넣기
  const id = await startFromGate(page, name);
  await page.locator('#ds-sp').fill('로비');
  await page.locator('#ds-sp').press('Enter');
  await expect(page.locator('[data-space="로비"]')).toHaveAttribute('aria-selected', 'true');
  const code = (await (await request.get(`/api/dss/v1/dss/${id}`)).json()).code as string;

  // Gate 를 다시 거쳐 같은 Storyboard 로 → 줄에 「작성 중 초안 있음」 · 「초안 이어 쓰기」 → 같은 초안(넣은 공간 그대로)
  expect(await startFromGate(page, name, true)).toBe(id);
  await expect(page.locator('.fl-footline')).toHaveCount(0);
  expect(code).toMatch(/^DSS-/);
  await expect(page.locator('[data-space="로비"]')).toBeVisible();
  expect((await draftsOf(request, sb.id)).map((d) => d.id)).toEqual([id]);
  // 서버도 같은 초안을 200 으로 돌려준다
  const again = await request.post('/api/dss/v1/dss', { data: { sb_id: sb.id } });
  expect(again.status()).toBe(200);
  expect((await again.json()).id).toBe(id);

  // 목록 → 초안 줄 × → 확인 → 빠짐(서버에서도 지워짐)
  await page.goto('/dss');
  await expect(page.getByRole('heading', { name: '공간별 제품 매칭 DSS', exact: true })).toBeVisible();
  await deleteDraftRow(page, name, 'DS0-draft-delete');
  expect((await request.get(`/api/dss/v1/dss/${id}`)).status()).toBe(404);
  await page.reload();
  await expect(page.getByRole('heading', { name: '공간별 제품 매칭 DSS', exact: true })).toBeVisible();
  await expect(page.locator('.fl-tr').filter({ hasText: name })).toHaveCount(0);

  // 지운 뒤 다시 시작하면 새 초안
  const id2 = await startFromGate(page, name);
  expect(id2).not.toBe(id);
  await expect(page.getByText('공간 0 · 제품 0')).toBeVisible();
  expect((await request.delete(`/api/dss/v1/dss/${id2}`)).status()).toBe(204);     // 정리
});
