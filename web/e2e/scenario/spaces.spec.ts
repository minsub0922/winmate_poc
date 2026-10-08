/**
 * 새 공간 시나리오 흐름(2026-10-08 보드 webapp1 SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC_Done) — 공간 → 시나리오 → 장면.
 * 실제 스택(mock 모델 — 로비 AI 3안은 고정 응답). 칸 폭(196 · 236)이 보드와 같은지 함께 본다.
 */
import { expect, test } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SCREENS = path.join(path.dirname(fileURLToPath(import.meta.url)), '__screens__');
const P = (name: string, kind = 'product') => ({ name, kind });

test('공간 → 시나리오 → 장면 — AI 3안 수락 · 제품 없는 공간 막기 · 자유 항목 · 저장', async ({ page, request }) => {
  test.setTimeout(180_000);
  const r = await request.post('/api/scenario/v1/space-sets', { data: { title: '용산 AI Ready 오피스', sb_id: 'SB-01', spaces: [
    { name: '로비', products: [P('The Wall IAB 146"'), P('Smart Signage QM55C'), P('삼성 키오스크'), P('MagicINFO', 'solution')] },
    { name: '주차장', products: [P('옥외형 사이니지 OHC55')] },
  ] } });
  expect(r.status()).toBe(201);
  const d = await r.json();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/scenario/spaces/${d.id}`);
  await expect(page.getByRole('heading', { name: '공간마다 시나리오를 여러 개 써요' })).toBeVisible();
  expect(Math.round((await page.locator('.ss-spaces').boundingBox())!.width)).toBe(196);

  // AI 3안(로비) → 점선 후보 3 → A 수락
  await page.getByRole('button', { name: /AI 시나리오 3안/ }).click();
  await expect(page.locator('.ss-sc--cand')).toHaveCount(3);
  expect(Math.round((await page.locator('.ss-grid2 > .wm-flow__panel').first().boundingBox())!.width)).toBe(236);
  await page.screenshot({ path: path.join(SCREENS, 'SC2_AI-new.png') });
  await page.getByRole('status').getByRole('button', { name: '수락' }).click();
  await expect(page.locator('.ss-sc--cand')).toHaveCount(2);
  await expect(page.getByRole('tab', { name: /로비/ })).toContainText('시나리오 1');

  // 주차장 제품을 빼면 경고 · 저장 막힘
  await page.getByRole('tab', { name: /주차장/ }).click();
  await page.getByRole('button', { name: '옥외형 사이니지 OHC55 빼기' }).click();
  await expect(page.getByText('공간마다 제품 · 솔루션이 하나 이상 있어야 해요')).toBeVisible();
  await expect(page.getByRole('button', { name: '저장', exact: true })).toBeDisabled();
  await page.screenshot({ path: path.join(SCREENS, 'SC2_Empty-new.png') });

  // 다시 넣기(고르기 대화상자 · 직접 추가) → 새 시나리오 · 자유 항목
  await page.getByRole('button', { name: '+ 추가 · 변경' }).click();
  const dlg = page.getByRole('dialog', { name: /주차장 · 제품 · 솔루션 고르기/ });
  await dlg.locator('#wm-pick-search').fill('옥외형 사이니지 OHC55');
  await dlg.getByRole('checkbox', { name: /옥외형 사이니지 OHC55/ }).first().click();
  await dlg.getByRole('button', { name: '완료' }).click();
  await page.getByRole('button', { name: '+ 시나리오 추가' }).click();
  await page.locator('#ss-title').fill('야간 주차 안내');
  await page.locator('#ss-who').fill('야근 후 퇴근하는 임직원');
  await page.locator('#ss-step-0').fill('주차장 입구 사이니지에 빈 층이 뜸');
  await page.getByRole('button', { name: '+ 쓰인 제품' }).click();
  await page.getByRole('button', { name: '+ 시간대' }).click();
  await page.locator('#ss-f-0').fill('오후 9시 이후');
  await page.waitForTimeout(1200);           // 자동 저장
  await page.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByRole('heading', { name: '공간 시나리오를 저장했어요' })).toBeVisible();
  await expect(page.getByText(/"stages\.sc": \{/)).toBeVisible();
  await page.screenshot({ path: path.join(SCREENS, 'SC_Done-new.png') });
  const st = await (await request.get(`/api/scenario/v1/space-sets/${d.id}/stage`)).json();
  const park = st.stage.spaces.find((s: { name: string }) => s.name === '주차장');
  expect(park.scenarios[0].steps[0].product).toBe('옥외형 사이니지 OHC55');
  expect(park.scenarios[0].fields).toEqual([{ k: '시간대', v: '오후 9시 이후' }]);
});
