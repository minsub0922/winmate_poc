/**
 * 고객 요구사항 저장 전 초안(보드 v62 RQ_Draft · 목록 × 는 보드에 없음 · 2026-10-10) — 실제 스택(MODEL_MODE=mock).
 * 새 요구사항(빈 최종본 + ① 입력 팝업)에 첫 글자를 넣으면 초안이 생긴다(주소만 바뀌고 팝업 그대로) → 팝업을 닫으면 작성 중 최종본(RQ_Draft)
 * → 목록에서 작성 중을 열면 ① 입력 팝업이 열린 채로(처음 한 번) → 목록(보드 List)의 초안 줄에 손을 올리면 × → 확인 → 지운다(`DELETE /v1/rq-flows/{id}` 204).
 * 저장한 요구사항(Storyboard 자동 생성)은 × 가 없고, API 로 지우려 해도 409 SAVED_CONTENT. (요구사항은 Gate 가 없어 「다시 시작」 중복은 없다)
 * 실행: WM_E2E_SUITE=requirements WM_E2E_DEV=1 WM_E2E_PORT=5201 npx playwright test e2e/requirements/rq-draft.spec.ts --workers=1
 */
import { expect, test, type Page } from '@playwright/test';
import { shot } from './helpers';

const tag = () => Date.now().toString(36).slice(-4);

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

test('RQ 초안 — 새 요구사항 첫 입력 → 목록 초안 줄 × 로 지우기 · 저장한 것은 지울 수 없음', async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const title = `성수 초안 ${tag()}`;

  // 새 요구사항 — 첫 입력 때 초안이 생기고 주소가 /requirements/flow/rqf_…?step=input 로(같은 팝업)
  await page.goto('/requirements/new');
  const dlg = page.locator('.fl-stepdlg');
  await expect(dlg.getByRole('heading', { name: '고객 요구사항 입력' })).toBeVisible();
  await dlg.locator('#rq-proj').fill(title);
  await expect(page).toHaveURL(/\/requirements\/flow\/rqf_[0-9A-Za-z]+\?step=input$/, { timeout: 15_000 });
  await expect(dlg).toBeVisible();
  const id = new URL(page.url()).pathname.split('/').pop()!;
  await expect.poll(async () => (await (await request.get(`/api/requirements/v1/rq-flows/${id}`)).json()).title, { timeout: 10_000 }).toBe(title);

  // 팝업 닫기 → 작성 중 최종본(RQ_Draft) · 「이어서 · 요구사항 입력」
  await dlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(dlg).toHaveCount(0);
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'draft');
  await expect(page.locator('.fl-detail .fl-dver')).toHaveText('작성 중 0/1');
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(title);
  await expect(page.locator('[data-slot="1"]').getByRole('button', { name: '이어서 · 요구사항 입력' })).toBeVisible();

  // 목록에서 작성 중을 열면 ① 입력 팝업이 열린 채로(처음 한 번) — Esc 로 닫으면 작성 중 최종본
  await page.goto('/requirements');
  await page.locator('.fl-card').filter({ hasText: title }).locator('.fl-cardtitle').click();
  await expect(page).toHaveURL(new RegExp(`/requirements/flow/${id}\\?step=input$`));
  await expect(dlg.locator('#rq-proj')).toHaveValue(title);
  await expect(dlg.locator('.fl-shead__mode')).toHaveText('새로 만들기');
  await page.keyboard.press('Escape');
  await expect(dlg).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/requirements/flow/${id}$`));
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'draft');

  // 목록 → 초안 줄 × → 확인 → 빠짐(서버에서도 지워짐)
  await page.goto('/requirements');
  await expect(page.getByRole('heading', { name: '고객 요구사항', exact: true })).toBeVisible();
  await deleteDraftRow(page, title, 'RQ0-draft-delete');
  expect((await request.get(`/api/requirements/v1/rq-flows/${id}`)).status()).toBe(404);
  await page.reload();
  await expect(page.getByRole('heading', { name: '고객 요구사항', exact: true })).toBeVisible();
  await expect(page.locator('.fl-card').filter({ hasText: title })).toHaveCount(0);

  // 저장한 요구사항(Storyboard 에 연결) — 목록 줄에 × 가 없고, 지우려 하면 409 SAVED_CONTENT
  const savedTitle = `성수 저장 ${tag()}`;
  const s = await (await request.post('/api/requirements/v1/rq-flows', { data: { title: savedTitle, keymen: [{ role: '자산관리팀장', weight: 100, reqs: [{ text: '1층 파사드 미디어로 집객' }] }] } })).json();
  const fin = await request.post(`/api/requirements/v1/rq-flows/${s.id}:finish`);
  expect(fin.ok(), await fin.text()).toBeTruthy();
  const del = await request.delete(`/api/requirements/v1/rq-flows/${s.id}`);
  expect(del.status()).toBe(409);
  expect((await del.json()).error).toMatchObject({ code: 'SAVED_CONTENT', message: '저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요' });
  await page.reload();
  const savedRow = page.locator('.fl-card').filter({ hasText: savedTitle });
  await expect(savedRow).toHaveCount(1);
  await expect(savedRow).toContainText(`${s.code} v1`);
  await savedRow.hover();
  await expect(savedRow.getByRole('button', { name: /지우기$/ })).toHaveCount(0);
});
