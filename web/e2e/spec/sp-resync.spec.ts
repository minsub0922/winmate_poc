/**
 * Spec 시트 새 흐름 — DSS 다시 가져오기 · 초안 지우기 · 같은 Storyboard 초안 이어 쓰기(2026-10-10 · 보드에 없음).
 * Storyboard(rq → dss) → `/spec/new?sb=&auto=1` → SP2 → 허브에 바뀐 DSS(판 +1: 삼성 키오스크 빠짐 · Smart Signage QH55C 새로)를 넣고 →
 * 편집 화면 머리 아래 안내 줄(AiBar) · 「다시 가져오기」 → 행 더함(DSS에서 새로) · 빠진 행 경고(DSS에서 빠짐) · 지우기 → 목록에서 초안 지우기.
 * 안내 줄이 있으면 그 줄(38 + 사이 12)만큼 작업 그리드가 줄고 칸 폭(330 · 756)은 그대로다. 캡처 `__screens__/SP2-resync-new.png` · `SP2-resynced-new.png`.
 * 실행: cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=spec WM_E2E_DEV=1 WM_E2E_PORT=5206 npx playwright test e2e/spec/sp-resync.spec.ts --workers=1
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { DSS_VALUE, internalHeaders, makeStoryboard, shotTo, tag } from '../shell/flowkit';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '__screens__');
const shot = async (page: Page, name: string) => { await page.mouse.move(10, 890); await shotTo(page, DIR, name); };
const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };

/** DSS_VALUE 에서 로비의 삼성 키오스크를 빼고 Smart Signage QH55C 를 더한 판 */
function dssV2() {
  const v = JSON.parse(JSON.stringify(DSS_VALUE)) as typeof DSS_VALUE;
  const lobby = v.spaces[0];
  lobby.products = [...lobby.products.filter((p) => p.name !== '삼성 키오스크'),
    { name: 'Smart Signage QH55C', kind: 'product', ref: null, qty: '1대', by: 'manual' } as (typeof lobby.products)[number]];
  return v;
}

test('Spec 시트 — DSS 다시 가져오기(안내 줄 · 행 추가 · DSS에서 빠짐 · 지우기) · 초안 이어 쓰기 · 목록에서 초안 지우기', async ({ page, request }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `용산 AI Ready 오피스 ${tag()}`;
  const sb = await makeStoryboard(request, { dss: true, name });
  const dss0 = (await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.dss as { ref: string; ver: number };

  await page.goto(`/spec/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/spec\/flow\/sfl_[0-9A-Za-z]+$/, { timeout: 30_000 });
  const fid = page.url().split('/').pop()!;
  const rows = page.getByTestId('sf-row');
  await expect(rows).toHaveCount(6);
  await expect(page.getByTestId('sf-dss-changed')).toHaveCount(0);
  const before = await box(page.getByTestId('sf-products'));
  expect(before).toEqual({ x: 300, y: 261, w: 330, h: 559 });     // 보드 SP2 그대로(sp-flow.spec 과 같은 값)

  // 같은 Storyboard 로 다시 시작(Gate · 자동) → 새 시트가 아니라 저장 전 초안으로
  await page.goto(`/spec/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(new RegExp(`/spec/flow/${fid}$`), { timeout: 30_000 });

  // 허브의 DSS 가 바뀜(판 +1)
  const put = await request.put(`/api/storyboard/v1/flows/${sb.id}/stages/dss`, {
    headers: internalHeaders('dss'),
    data: { ref: dss0.ref, ver: dss0.ver + 1, value: dssV2(), md: '- 업종: 오피스 · 업무시설 · 공간 3\n- 로비: The Wall IAB 146" · Smart Signage QM55C ×2 · Smart Signage QH55C' },
  });
  expect(put.ok()).toBe(true);
  await page.reload();
  const line = page.getByTestId('sf-dss-changed');
  await expect(line).toHaveText(`Storyboard의 DSS가 바뀌었어요 · ${dss0.ref} v${dss0.ver} → v${dss0.ver + 1} · 제품 1 추가 · 1 빠짐`);
  const bar = page.locator('.wm-aibar').filter({ has: line });
  await expect(bar.getByRole('button', { name: '다시 가져오기' })).toBeVisible();
  // 안내 줄(38 · 머리 아래) — 작업 그리드만 그만큼(38 + 12) 줄고 칸 폭 · 시트 만들기 버튼 자리는 그대로
  expect(await box(bar)).toMatchObject({ x: 300, w: 1100, h: 38 });
  expect(await box(page.getByTestId('sf-products'))).toEqual({ x: 300, y: 261 + 50, w: 330, h: 559 - 50 });
  expect((await box(page.getByTestId('sf-preview'))).w).toBe(756);
  expect(await box(page.getByRole('button', { name: '시트 만들기' }))).toMatchObject({ y: 832, h: 48 });
  await expect(rows).toHaveCount(6);                                 // 다시 가져오기 전에는 그대로
  await shot(page, 'SP2-resync-new');

  // 다시 가져오기 → 토스트 · 안내 줄 사라짐 · QH55C 행 더함(DSS에서 새로 · KB 모델) · 키오스크는 남기고 「DSS에서 빠짐」
  await bar.getByRole('button', { name: '다시 가져오기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: 'DSS를 다시 가져왔어요 · 제품 1 추가 · 1개 「DSS에서 빠짐」 표시' })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('sf-dss-changed')).toHaveCount(0);
  await expect(rows).toHaveCount(7);
  const qh = page.locator('[data-row="Smart Signage QH55C"]');
  await expect(qh).toHaveAttribute('data-dss', 'added');
  await expect(qh.locator('.sf-row__sp')).toHaveText('로비 · DSS에서 새로');
  await expect(qh.locator('.sf-model')).toHaveText('QH55C');
  const kiosk = page.locator('[data-row="삼성 키오스크"]');
  await expect(kiosk).toHaveAttribute('data-dss', 'removed');
  await expect(kiosk.locator('.sf-row__sp')).toHaveText('로비 · DSS에서 빠짐');
  await expect(page.getByTestId('sf-preview').locator('.sf-cell--head')).toContainText(['Smart Signage QH55C']);
  expect(await box(page.getByTestId('sf-products'))).toEqual(before);   // 안내 줄이 없어지면 보드 자리로
  await shot(page, 'SP2-resynced-new');
  const doc = await (await request.get(`/api/spec/v1/spec-flows/${fid}`)).json();
  expect(doc).toMatchObject({ dss_ref: dss0.ref, dss_ver: dss0.ver + 1, dss_changed: null });
  expect(doc.last_resync).toMatchObject({ added: ['Smart Signage QH55C'], removed: ['삼성 키오스크'] });
  expect(doc.rows.find((r: { name: string }) => r.name === 'Smart Signage QH55C')).toMatchObject({ by: 'dss', qty: 1, dss_status: 'added' });

  // 빠진 행 지우기(×)
  await kiosk.getByRole('button', { name: '삼성 키오스크 지우기' }).click();
  await expect(kiosk).toHaveCount(0);
  await expect(rows).toHaveCount(6);

  // 목록(SP0) — 저장 전 초안 줄의 × → 확인 → 지움(허브에는 간 적 없음)
  await page.goto('/spec');
  const row = page.getByRole('row').filter({ hasText: name });
  await expect(row).toContainText('작성 중');
  await row.hover();
  await row.getByRole('button', { name: `${name} 지우기` }).click();
  const dlg = page.getByRole('dialog').filter({ hasText: '작성 중인 초안을 지울까요?' });
  await expect(dlg).toBeVisible();
  await dlg.getByRole('button', { name: '지우기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: '초안을 지웠어요' })).toBeVisible();
  await expect(page.getByRole('row').filter({ hasText: name })).toHaveCount(0);
  expect((await request.get(`/api/spec/v1/spec-flows/${fid}`)).status()).toBe(404);
  // 저장한 시트는 지울 수 없다(409) — 목록 줄에도 × 가 없다
  const made = await (await request.post('/api/spec/v1/spec-flows', { data: { sb_id: sb.id } })).json();
  expect((await request.post(`/api/spec/v1/spec-flows/${made.id}:finish`)).ok()).toBe(true);
  const del = await request.delete(`/api/spec/v1/spec-flows/${made.id}`);
  expect(del.status()).toBe(409);
  expect((await del.json()).error).toMatchObject({ code: 'SAVED_CONTENT', message: '저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요' });
  await page.reload();
  const savedRow = page.getByRole('row').filter({ hasText: `${made.code} v1` });
  await expect(savedRow).toBeVisible();
  await expect(savedRow.locator('.fl-del')).toHaveCount(0);
});
