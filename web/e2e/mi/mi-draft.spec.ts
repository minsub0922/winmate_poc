/**
 * MI 저장 전 초안(보드에 없음 · 2026-10-10 · 팝업 모델 보드 v62) — 실제 스택(MODEL_MODE=mock · mocks/ai-tools/mi.flow_analyze.v1).
 * ② 검색 팝업을 닫으면 작성 중 최종본 → Gate(/mi/new)에서 같은 Storyboard 로 다시 시작하면 같은 초안을 이어서 연다
 * (분석을 다시 돌리지 않음 · `POST /v1/mi-flows` 200 · ② 검색 팝업이 열린 채로) → 목록 「열기」도 이어서 할 단계 팝업 →
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
  const row = page.locator('.fl-card').filter({ hasText: title });
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

test('MI 초안 — 팝업을 닫으면 작성 중 · Gate 를 다시 거쳐도 같은 초안 · 목록 「열기」는 이어서 할 단계 팝업 · × 로 지우기', async ({ page, request }) => {
  test.setTimeout(150_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makeStoryboard(request, { dss: true, name: `용산 초안 ${tag()}` });
  const title = `${sb.name} 시장 분석`;

  // Gate 팝업 → 시작 → ② 분석 로딩 → MI2
  await page.goto('/mi/new');
  const mine = page.getByRole('radio', { name: new RegExp(sb.name) });
  await mine.click();
  await page.getByRole('button', { name: /이 Storyboard로 시작/ }).click();
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}\?step=search$/);
  const id = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  const doc = await (await request.get(`/api/mi/v1/mi-flows/${id}`)).json();
  const jobs = doc.progress.job_id as string;

  // ② 팝업 닫기 → 작성 중 최종본(작성 중 1/3 · ② 자리표시 「이어서 · 검색」)
  const stepDlg = page.locator('.fl-stepdlg');
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(stepDlg).toHaveCount(0);
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'draft');
  await expect(page.locator('.fl-detail .fl-dver')).toHaveText('작성 중 1/3');

  // Gate(이 Storyboard · 저장 전 초안이 있어 「작성 중 초안 있음」) → 「초안 이어 쓰기」 → 같은 초안의 ② 팝업 · 분석을 다시 돌리지 않음
  await page.goto(`/mi/new?sb=${sb.id}`);
  const again = page.getByRole('radio', { name: new RegExp(sb.name) });
  await expect(again).toHaveAttribute('aria-checked', 'true');
  await expect(again).toContainText('작성 중 초안 있음');
  await expect(page.locator('.fl-footline')).toContainText(`작성 중이던 ${doc.code} 초안을 이어서 열어요`);
  await page.mouse.move(10, 890);
  await shot(page, 'MI1-draft-new');
  await page.getByRole('button', { name: /초안 이어 쓰기/ }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${id}\\?step=search$`));
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible();
  expect((await draftsOf(request, sb.id)).map((d) => d.id)).toEqual([id]);
  expect((await (await request.get(`/api/mi/v1/mi-flows/${id}`)).json()).progress.job_id).toBe(jobs);   // 새 분석 잡 없음
  // 서버도 같은 초안을 200 으로 돌려준다
  const re = await request.post('/api/mi/v1/mi-flows', { data: { sb_id: sb.id } });
  expect(re.status()).toBe(200);
  expect((await re.json()).id).toBe(id);

  // 목록 「열기」(작성 중) → 이어서 할 단계 팝업(② 검색)이 열린 채로
  await page.goto('/mi');
  await expect(page.getByRole('heading', { level: 1, name: 'Market Intelligence' })).toBeVisible();
  await page.locator('.fl-card').filter({ hasText: title }).locator('.fl-cardtitle').click();
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${id}\\?step=search$`));
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible();
  // 주소로 ③ 을 열어도 웹 검색 전이면 ② 로
  await page.goto(`/mi/flow/${id}?step=refine`);
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${id}\\?step=search$`));

  // 목록 → 초안 줄 × → 확인 → 빠짐(서버에서도 지워짐)
  await page.goto('/mi');
  await expect(page.getByRole('heading', { level: 1, name: 'Market Intelligence' })).toBeVisible();
  await deleteDraftRow(page, title, 'MI0-draft-delete');
  expect((await request.get(`/api/mi/v1/mi-flows/${id}`)).status()).toBe(404);
  await page.reload();
  await expect(page.getByRole('heading', { level: 1, name: 'Market Intelligence' })).toBeVisible();
  await expect(page.locator('.fl-card').filter({ hasText: title })).toHaveCount(0);
  expect(await draftsOf(request, sb.id)).toEqual([]);
});

test('MI 초안 — 웹 검색까지 마친 초안은 ③ 정제 팝업으로 이어서 · 닫으면 작성 중 2/3(검색 조건 줄 + ③ 「이어서 · 정제」)', async ({ page, request }) => {
  test.setTimeout(150_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makeStoryboard(request, { dss: true, name: `용산 정제 초안 ${tag()}` });
  await page.goto(`/mi/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}\?step=search$/);
  const id = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  await page.getByRole('button', { name: '웹 검색 후 정제로' }).click();
  await expect(page.getByRole('heading', { level: 1, name: '찾은 정보를 정리해요' })).toBeVisible({ timeout: 30_000 });
  await expect(page).toHaveURL(/\?step=refine$/);

  // 닫기 → 작성 중 2/3: 검색 조건 줄은 채워지고 ③ 은 「이어서 · 정제」
  const stepDlg = page.locator('.fl-stepdlg');
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(stepDlg).toHaveCount(0);
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'draft');
  await expect(view.locator('.fl-dver')).toHaveText('작성 중 2/3');
  await expect(view.locator('.miv-bar')).toBeVisible();
  await expect(view.locator('.miv-bar__q')).toHaveText('시장 4 · 고객사 3 · 사용자 3 · 프라임 오피스 스마트 빌딩 도입 외');
  await expect(view.locator('[data-slot="2"]')).toHaveCount(0);
  await expect(view.locator('[data-slot="3"]').getByRole('button', { name: '이어서 · 정제' })).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'MI_Draft2-new');

  // 목록 「열기」 → ③ 정제 팝업이 열린 채로 · Gate 「초안 이어 쓰기」(?step=search)도 ③ 으로
  await page.goto('/mi');
  await page.locator('.fl-card').filter({ hasText: `${sb.name} 시장 분석` }).locator('.fl-cardtitle').click();
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${id}\\?step=refine$`));
  await expect(page.getByRole('heading', { level: 1, name: '찾은 정보를 정리해요' })).toBeVisible();
  await page.goto(`/mi/new?sb=${sb.id}`);
  await page.getByRole('button', { name: /초안 이어 쓰기/ }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${id}\\?step=refine$`));
  await expect(page.getByRole('heading', { level: 1, name: '찾은 정보를 정리해요' })).toBeVisible();
  // 「검색어 고치기」 → ② (작성 중이어도 같은 팝업 안에서)
  await stepDlg.getByRole('button', { name: '검색어 고치기' }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${id}\\?step=search$`));
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible();
  expect((await request.delete(`/api/mi/v1/mi-flows/${id}`)).status()).toBe(204);    // 정리
});
