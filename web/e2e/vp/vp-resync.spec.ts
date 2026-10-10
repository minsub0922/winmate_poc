/**
 * 새 VP 흐름 — DSS 다시 가져오기 · 초안 지우기 · 같은 Storyboard 초안 이어 쓰기(2026-10-10 · 보드에 없음).
 * Storyboard(rq → dss) → `/vp/new?sb=&auto=1` → VP2(DSS 제품 · 솔루션 모두 고른 채로) → 허브에 바뀐 DSS(판 +1: 삼성 키오스크 빠짐 · Smart Signage QH55C 새로)를 넣고 →
 * 머리 아래 안내 줄(AiBar) · 「다시 가져오기」 → 골라 둔 키오스크는 남기고 「DSS에서 빠짐」 · QH55C 는 고르기 대화상자의 새 후보(자동으로 고르지 않음) → 목록에서 초안 지우기.
 * 안내 줄만큼(38 + 사이 12) 작업 그리드가 줄고 왼쪽 280 · 본문 1180 은 그대로. 캡처 `__screens__/VP2-resync-new.png` · `VP2-resynced-new.png`.
 * 실행: cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=vp WM_E2E_DEV=1 WM_E2E_PORT=5205 npx playwright test e2e/vp/vp-resync.spec.ts --workers=1
 */
import { test, type Locator } from '@playwright/test';
import { DSS_VALUE, internalHeaders, makeStoryboard, tag } from '../shell/flowkit';
import { expect, shot } from './helpers';

const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };

/** DSS_VALUE 에서 로비의 삼성 키오스크를 빼고 Smart Signage QH55C 를 더한 판 */
function dssV2() {
  const v = JSON.parse(JSON.stringify(DSS_VALUE)) as typeof DSS_VALUE;
  const lobby = v.spaces[0];
  lobby.products = [...lobby.products.filter((p) => p.name !== '삼성 키오스크'),
    { name: 'Smart Signage QH55C', kind: 'product', ref: null, qty: '1대', by: 'manual' } as (typeof lobby.products)[number]];
  return v;
}

test('VP — DSS 다시 가져오기(안내 줄 · 새 후보 · DSS에서 빠짐) · 초안 이어 쓰기 · 목록에서 초안 지우기', async ({ page, request }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `용산 AI Ready 오피스 ${tag()}`;
  const sb = await makeStoryboard(request, { dss: true, name });
  const dss0 = (await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.dss as { ref: string; ver: number };

  await page.goto(`/vp/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/vp\/values\/vmap_[0-9A-Za-z]+$/, { timeout: 30_000 });
  const mapId = page.url().split('/').pop()!;
  await expect(page.getByRole('heading', { name: '제품 · 솔루션마다 가치와 고객의 니즈를 적어요' })).toBeVisible();
  await expect(page.getByRole('button', { name: /제품 · 솔루션 고르기 · 8/ })).toBeVisible();          // DSS 제품 6 + 솔루션 2
  await expect(page.getByTestId('vv-dss-changed')).toHaveCount(0);
  const left = page.locator('.wm-flow__grid > .wm-flow__panel').first();
  const left0 = await box(left);
  expect(left0.w).toBe(280);

  // 같은 Storyboard 로 다시 시작(Gate · 자동) → 저장 전 초안으로
  await page.goto(`/vp/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(new RegExp(`/vp/values/${mapId}$`), { timeout: 30_000 });

  // 허브의 DSS 가 바뀜(판 +1)
  const put = await request.put(`/api/storyboard/v1/flows/${sb.id}/stages/dss`, {
    headers: internalHeaders('dss'),
    data: { ref: dss0.ref, ver: dss0.ver + 1, value: dssV2(), md: '- 업종: 오피스 · 업무시설 · 공간 3' },
  });
  expect(put.ok()).toBe(true);
  await page.reload();
  const line = page.getByTestId('vv-dss-changed');
  await expect(line).toHaveText(`Storyboard의 DSS가 바뀌었어요 · ${dss0.ref} v${dss0.ver} → v${dss0.ver + 1} · 제품 1 추가 · 1 빠짐`);
  const bar = page.locator('.wm-aibar').filter({ has: line });
  expect(await box(bar)).toMatchObject({ x: 300, w: 1100, h: 38 });
  expect(await box(left)).toEqual({ ...left0, y: left0.y + 50, h: left0.h - 50 });
  expect(Math.round((await page.locator('.wm-flow').boundingBox())!.width)).toBe(1180);
  await page.mouse.move(0, 0);
  await shot(page, 'VP2-resync-new');

  // 다시 가져오기 → 골라 둔 키오스크는 남기고 「DSS에서 빠짐」 · QH55C 는 고르지 않은 새 후보
  await bar.getByRole('button', { name: '다시 가져오기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: 'DSS를 다시 가져왔어요 · 새 후보 1(고르기에서) · 고른 것 1개 「DSS에서 빠짐」' }))
    .toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('vv-dss-changed')).toHaveCount(0);
  const kiosk = page.getByRole('button', { name: /삼성 키오스크/ });
  await expect(kiosk).toContainText('가치 없음 · DSS에서 빠짐');
  await expect(page.getByRole('button', { name: /제품 · 솔루션 고르기 · 8/ })).toBeVisible();          // 자동으로 고르지 않음
  expect(await box(left)).toEqual(left0);
  await kiosk.click();
  await expect(page.locator('.vv-rhead__where')).toContainText('DSS에서 빠짐');
  await page.mouse.move(0, 0);
  await shot(page, 'VP2-resynced-new');
  await page.getByRole('button', { name: /제품 · 솔루션 고르기 · 8/ }).click();
  const dlg = page.getByRole('dialog', { name: 'VP에 넣을 제품 · 솔루션 고르기' });
  const qh = dlg.getByRole('checkbox', { name: /Smart Signage QH55C/ });
  await expect(qh).toHaveAttribute('aria-checked', 'false');
  await expect(qh).toContainText('DSS · 로비 · 새로');
  await qh.click();
  await expect(qh).toHaveAttribute('aria-checked', 'true');
  await dlg.getByRole('button', { name: '완료' }).click();
  await expect(page.getByRole('button', { name: /제품 · 솔루션 고르기 · 9/ })).toBeVisible();
  const doc = await (await request.get(`/api/vp/v1/value-maps/${mapId}`)).json();
  expect(doc).toMatchObject({ dss_ref: dss0.ref, dss_ver: dss0.ver + 1, dss_changed: null });
  expect(doc.last_resync).toMatchObject({ added: ['Smart Signage QH55C'], kept: ['삼성 키오스크'] });
  expect(doc.items.find((i: { name: string }) => i.name === '삼성 키오스크')).toMatchObject({ dss_status: 'removed', from_dss: false });

  // 목록(VP0) — 저장 전 초안 줄의 × → 확인 → 지움
  await page.goto('/vp');
  const row = page.getByRole('row').filter({ hasText: name });
  await expect(row).toContainText('작성 중');
  await row.hover();
  await row.getByRole('button', { name: `${name} 지우기` }).click();
  await page.getByRole('dialog').filter({ hasText: '작성 중인 초안을 지울까요?' }).getByRole('button', { name: '지우기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: '초안을 지웠어요' })).toBeVisible();
  await expect(page.getByRole('row').filter({ hasText: name })).toHaveCount(0);
  expect((await request.get(`/api/vp/v1/value-maps/${mapId}`)).status()).toBe(404);
  // 저장한 맵은 지울 수 없다(409 SAVED_CONTENT)
  const made = await (await request.post('/api/vp/v1/value-maps', { data: { sb_id: sb.id } })).json();
  expect(made.id).not.toBe(mapId);
  await request.post(`/api/vp/v1/value-maps/${made.id}/items/${made.items[0].key}/values`, { data: { space: '로비', message: '들어서는 순간 AI 비전을 보여 줌' } });
  expect((await request.post(`/api/vp/v1/value-maps/${made.id}:finish`)).ok()).toBe(true);
  const del = await request.delete(`/api/vp/v1/value-maps/${made.id}`);
  expect(del.status()).toBe(409);
  expect((await del.json()).error.code).toBe('SAVED_CONTENT');
});
