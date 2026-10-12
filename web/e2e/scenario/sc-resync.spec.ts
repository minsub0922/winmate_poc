/**
 * 공간 시나리오 상세(웹앱 ① v63) — DSS 다시 가져오기 · 초안 지우기 · 같은 Storyboard 초안 이어 쓰기(2026-10-10 · 보드에 없음).
 * Storyboard(rq → dss) → `/scenario/new?sb=&auto=1` → 상세(로비에 키오스크를 쓰는 시나리오) → 허브에 바뀐 DSS(판 +1: 로비 키오스크 빠짐 · QH55C 새로 ·
 * 새 공간 라운지(QM55C))를 넣고 → 본문 위 안내 줄(AiBar) · 「다시 가져오기」 → 새 공간 · 새 제품(새로) · 시나리오가 쓰는 빠진 제품은 남기고 「DSS에서 빠짐」
 * → 목록에서 초안 지우기. 안내 줄만큼(38 + 사이 12) 본문 그리드가 줄고 칸 폭(220 · 866)은 그대로. 캡처 `__screens__/SC2-resync.png` · `SC2-resynced.png`.
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { DSS_VALUE, internalHeaders, makeStoryboard, tag } from '../shell/flowkit';
import { shot } from './helpers';

const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
/** 캡처 전 — 마우스를 치우고 앞 단계 토스트가 사라질 때까지(보드에는 토스트가 없다) */
const still = async (page: Page) => { await page.mouse.move(0, 0); await expect(page.locator('.wm-toast')).toHaveCount(0, { timeout: 8_000 }); await page.waitForTimeout(300); };

/** DSS_VALUE 에서 로비의 삼성 키오스크를 빼고 Smart Signage QH55C 를 더하고, 새 공간 라운지(QM55C)를 둔 판 */
function dssV2() {
  const v = JSON.parse(JSON.stringify(DSS_VALUE)) as typeof DSS_VALUE;
  type P = (typeof v.spaces)[number]['products'][number];
  const lobby = v.spaces[0];
  lobby.products = [...lobby.products.filter((p) => p.name !== '삼성 키오스크'), { name: 'Smart Signage QH55C', kind: 'product', ref: null, qty: '1대', by: 'manual' } as P];
  v.spaces.push({ name: '라운지', by: 'manual', products: [{ name: 'Smart Signage QM55C', kind: 'product', ref: 'kb:model:mdl_LH55QMCEBGCXKR', qty: '1대', by: 'manual' } as P] });
  return v;
}

test('공간 시나리오 — DSS 다시 가져오기(안내 줄 · 새 공간 · 새 제품 · DSS에서 빠짐) · 초안 이어 쓰기 · 목록에서 초안 지우기', async ({ page, request }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `용산 AI Ready 오피스 ${tag()}`;
  const sb = await makeStoryboard(request, { dss: true, name });
  const dss0 = (await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.dss as { ref: string; ver: number };

  await page.goto(`/scenario/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/scenario\/spaces\/scs_[^/]+$/, { timeout: 30_000 });
  const setId = page.url().split('/').pop()!;
  await expect(page.locator('.ss-sp')).toHaveText([/로비/, /회의실/, /주차장/]);
  await expect(page.getByTestId('ss-dss-changed')).toHaveCount(0);
  const spaces0 = await box(page.locator('.ss-spaces'));

  // 로비: 공간 제품을 모두 쓰는 직접 시나리오(키오스크 포함) — 자동 저장
  await page.getByRole('button', { name: '+ 시나리오 추가' }).click();
  const c = page.locator('.ss-card').last();
  await c.getByRole('textbox', { name: '시나리오 이름' }).fill('무인 방문 접수');
  await c.getByRole('textbox', { name: '시나리오 이름' }).press('Enter');
  await c.getByRole('textbox', { name: '장면 1' }).fill('키오스크에서 방문 접수');
  await c.getByRole('textbox', { name: '장면 1' }).press('Enter');
  await expect(c.locator('.ss-tchip--on')).toHaveCount(4);
  await expect.poll(async () => (await (await request.get(`/api/scenario/v1/space-sets/${setId}`)).json()).counts.scenarios, { timeout: 10_000 }).toBe(1);

  // 같은 Storyboard 로 다시 시작(팝업 · 자동) → 저장 전 초안으로
  await page.goto(`/scenario/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(new RegExp(`/scenario/spaces/${setId}$`), { timeout: 30_000 });

  // 허브의 DSS 가 바뀜(판 +1)
  const put = await request.put(`/api/storyboard/v1/flows/${sb.id}/stages/dss`, {
    headers: internalHeaders('dss'),
    data: { ref: dss0.ref, ver: dss0.ver + 1, value: dssV2(), md: '- 업종: 오피스 · 업무시설 · 공간 4' },
  });
  expect(put.ok()).toBe(true);
  await page.reload();
  const line = page.getByTestId('ss-dss-changed');
  await expect(line).toHaveText(`Storyboard의 DSS가 바뀌었어요 · ${dss0.ref} v${dss0.ver} → v${dss0.ver + 1} · 제품 1 추가 · 1 빠짐 · 놓인 공간 1 바뀜 · 공간 1 추가`);
  const bar = page.locator('.wm-aibar').filter({ has: line });
  // 안내 줄(38) — 본문 열 1100 그대로, 칸 폭(220 · 866)은 그대로, 본문 그리드만 50 줄어든다
  expect(await box(bar)).toMatchObject({ x: 300, w: 1100, h: 38 });
  expect(await box(page.locator('.ss-spaces'))).toEqual({ ...spaces0, y: spaces0.y + 50, h: spaces0.h - 50 });
  expect((await box(page.locator('.ss-main'))).w).toBe(866);
  await still(page);
  await shot(page, 'SC2-resync');

  // 다시 가져오기 → 라운지(새 공간) · 로비 QH55C(새로) · 시나리오가 쓰는 키오스크는 남기고 「DSS에서 빠짐」 · 빈 주차장은 그대로(DSS 에 있음)
  await bar.getByRole('button', { name: '다시 가져오기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: 'DSS를 다시 가져왔어요 · 공간 1 추가 · 제품 2 추가 · 1개 「DSS에서 빠짐」' }))
    .toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('ss-dss-changed')).toHaveCount(0);
  await expect(page.locator('.ss-sp')).toHaveText([/로비/, /회의실/, /주차장/, /라운지/]);
  await expect(page.locator('.ss-sp', { hasText: '라운지' })).toContainText('시나리오 없음 · 제품 1 · 새 공간');
  await expect(page.locator('.ss-pchip')).toHaveText([/제품The Wall IAB 146"/, /제품Smart Signage QM55C/, /제품삼성 키오스크DSS에서 빠짐/, /솔루션MagicINFO/, /제품Smart Signage QH55C새로/]);
  await expect(page.locator('.ss-pchip[data-dss="removed"]')).toHaveClass(/ss-pchip--gone/);
  await expect(page.locator('.ss-card').first().locator('.ss-tchip--on')).toHaveCount(4);        // 시나리오는 그대로(새 제품은 시나리오에 넣지 않음)
  expect(await box(page.locator('.ss-spaces'))).toEqual(spaces0);
  await still(page);
  await shot(page, 'SC2-resynced');
  const doc = await (await request.get(`/api/scenario/v1/space-sets/${setId}`)).json();
  expect(doc).toMatchObject({ dss_ref: dss0.ref, dss_ver: dss0.ver + 1, dss_changed: null });
  expect(doc.last_resync).toMatchObject({ kept: ['로비 · 삼성 키오스크'], spaces_added: ['라운지'], added: ['로비 · Smart Signage QH55C', '라운지 · Smart Signage QM55C'] });

  // 목록(SC0) — 저장 전 초안 카드의 × → 확인 → 지움
  await page.goto('/scenario');
  const row = page.locator('.fl-card').filter({ hasText: name });
  await expect(row).toContainText('작성 중');
  await row.hover();
  await row.getByRole('button', { name: `${name} 지우기` }).click();
  const dlg = page.getByRole('dialog').filter({ hasText: '작성 중인 초안을 지울까요?' });
  await dlg.getByRole('button', { name: '지우기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: '초안을 지웠어요' })).toBeVisible();
  await expect(page.locator('.fl-card').filter({ hasText: name })).toHaveCount(0);
  expect((await request.get(`/api/scenario/v1/space-sets/${setId}`)).status()).toBe(404);
  // 저장한 묶음은 지울 수 없다(409 SAVED_CONTENT)
  const made = await (await request.post('/api/scenario/v1/space-sets', { data: { sb_id: sb.id } })).json();
  expect(made.id).not.toBe(setId);
  expect((await request.post(`/api/scenario/v1/space-sets/${made.id}:finish`)).ok()).toBe(true);
  const del = await request.delete(`/api/scenario/v1/space-sets/${made.id}`);
  expect(del.status()).toBe(409);
  expect((await del.json()).error.code).toBe('SAVED_CONTENT');
});
