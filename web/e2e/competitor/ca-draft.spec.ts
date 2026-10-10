/**
 * 경쟁사 분석 저장 전 초안(보드에 없음 · 2026-10-10) — 실제 스택(MODEL_MODE=mock).
 * Gate 를 다시 거쳐 같은 Storyboard 로 시작하면 같은 초안을 이어서 연다(새 초안이 늘지 않음 · `POST /v1/ca-flows` 200) →
 * 목록(보드 List)의 초안 줄에 손을 올리면 × → 확인 → 지운다(`DELETE /v1/ca-flows/{id}` 204).
 * 실행: WM_E2E_SUITE=competitor WM_E2E_DEV=1 WM_E2E_PORT=5204 npx playwright test e2e/competitor/ca-draft.spec.ts --workers=1
 */
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { shot } from './helpers';

/** Gate(보드 Gate) — 우리 Storyboard 를 골라 시작 → 편집 화면 id */
async function startFromGate(page: Page, name: string, resume = false) {
  await page.goto('/competitor/new');
  const row = page.getByRole('radio', { name: new RegExp(name) });
  await row.click();
  await expect(row).toHaveAttribute('aria-checked', 'true');
  // 저장 전 초안은 허브에 없다(「있음」이 아님) — 초안이 있으면 「작성 중 초안 있음」 · 「초안 이어 쓰기」
  await expect(row).toContainText(resume ? '작성 중 초안 있음' : '이어서 만들기');
  await page.getByRole('button', { name: resume ? /초안 이어 쓰기/ : /이 Storyboard로 시작/ }).click();
  await expect(page).toHaveURL(/\/competitor\/flow\/cflow_[0-9A-Za-z]+$/, { timeout: 20_000 });
  await expect(page.getByRole('heading', { name: '경쟁사를 리스트업하고 우리 제안과 비교해요' })).toBeVisible();
  return page.url().split('/').pop()!.split('?')[0];
}

const draftsOf = async (request: APIRequestContext, sbId: string) =>
  ((await (await request.get('/api/competitor/v1/ca-flows?limit=200')).json()).items as Array<{ id: string; sb_id: string | null }>).filter((d) => d.sb_id === sbId);

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

test('경쟁사 분석 초안 — Gate 를 다시 거쳐도 같은 초안 · 목록에서 × 로 지우기', async ({ page, request }) => {
  test.setTimeout(150_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makeStoryboard(request, { dss: true, name: `용산 경쟁 초안 ${tag()}` });
  const title = `${sb.name} 경쟁사`;

  // 처음 시작 → 경쟁사 하나 직접 추가(API · 웹 검색 없이)
  const id = await startFromGate(page, sb.name);
  const added = await request.post(`/api/competitor/v1/ca-flows/${id}/competitors`, { data: { name: '경쟁사 초안', lookup: false } });
  expect(added.status()).toBe(201);
  const code = (await added.json()).code as string;

  // Gate 를 다시 거쳐 같은 Storyboard 로 → 「초안 이어 쓰기」 → 같은 초안(더한 경쟁사 그대로)
  expect(await startFromGate(page, sb.name, true)).toBe(id);
  expect(code).toBeTruthy();
  // 서버도 같은 초안을 200 으로 돌려준다(Gate 를 거치지 않은 시작)
  const again = await page.request.post('/api/competitor/v1/ca-flows', { data: { sb_id: sb.id } });
  expect(again.status()).toBe(200);
  expect((await again.json()).id).toBe(id);
  await expect(page.getByText('경쟁사 초안').first()).toBeVisible();
  expect((await draftsOf(request, sb.id)).map((d) => d.id)).toEqual([id]);

  // 목록 → 초안 줄 × → 확인 → 빠짐(서버에서도 지워짐)
  await page.goto('/competitor');
  await expect(page.getByRole('heading', { name: '경쟁사 분석', exact: true })).toBeVisible();
  await deleteDraftRow(page, title, 'CA0-draft-delete');
  expect((await request.get(`/api/competitor/v1/ca-flows/${id}`)).status()).toBe(404);
  await page.reload();
  await expect(page.getByRole('heading', { name: '경쟁사 분석', exact: true })).toBeVisible();
  await expect(page.locator('.fl-tr').filter({ hasText: title })).toHaveCount(0);
  expect(await draftsOf(request, sb.id)).toEqual([]);
});
