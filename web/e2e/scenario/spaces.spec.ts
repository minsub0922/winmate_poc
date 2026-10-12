/**
 * 공간 시나리오 상세(웹앱 ① v63 · 보드 SCBody) — Storyboard 없이 공간 · 제품을 API 로 준 묶음(허브에 쓰지 않는다 — 허브 연동은 sc-flow.spec.ts).
 * 실제 스택(mock 모델 — 로비 AI 3안은 고정 응답). AI 3안 수락 · 제품 없는 공간 막기 · 자유 항목 · 저장 → 그 자리에서 저장됨.
 */
import { expect, test } from '@playwright/test';
import { shot } from './helpers';

const P = (name: string, kind = 'product') => ({ name, kind });

test('공간 → 시나리오 → 장면(Storyboard 없음) — AI 3안 수락 · 제품 없는 공간 막기 · 자유 항목 · 저장', async ({ page, request }) => {
  test.setTimeout(180_000);
  const r = await request.post('/api/scenario/v1/space-sets', { data: { title: '용산 AI Ready 오피스', spaces: [
    { name: '로비', products: [P('The Wall IAB 146"'), P('Smart Signage QM55C'), P('삼성 키오스크'), P('MagicINFO', 'solution')] },
    { name: '주차장', products: [P('옥외형 사이니지 OHC55')] },
  ] } });
  expect(r.status()).toBe(201);
  const d = await r.json();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/scenario/spaces/${d.id}`);
  const head = page.locator('.cd-head');
  await expect(head.getByRole('heading', { name: '용산 AI Ready 오피스' })).toBeVisible();
  await expect(head.locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(page.getByText('저장하면 이 요구사항으로 Storyboard가 자동으로 만들어져요')).toBeVisible();   // 셸 SBBar 빈 문구
  await expect(page.locator('.ss-spaces__h')).toHaveText('공간 · DSS');
  expect(Math.round((await page.locator('.ss-spaces').boundingBox())!.width)).toBe(220);

  // AI 3안(로비) → 점선 후보 3 → A 수락
  await page.getByRole('button', { name: /AI 시나리오 3안/ }).click();
  await expect(page.locator('.ss-card.cd-pend')).toHaveCount(3);
  await shot(page, 'SC2_AI-nosb');
  await page.locator('.ss-card.cd-pend').first().getByRole('button', { name: '수락' }).click();
  await expect(page.locator('.ss-card.cd-pend')).toHaveCount(2);
  await expect(page.locator('.ss-sp', { hasText: '로비' })).toContainText('시나리오 1');

  // 주차장 제품을 빼면 경고 · 저장 막힘
  await page.locator('.ss-sp', { hasText: '주차장' }).click();
  await page.getByRole('button', { name: '빼기 · 옥외형 사이니지 OHC55' }).click();
  await expect(page.locator('.ss-warnpill')).toHaveText('하나 이상 골라야 저장돼요');
  await expect(head.getByRole('button', { name: '저장', exact: true })).toHaveAttribute('aria-disabled', 'true');
  await shot(page, 'SC2_NoProduct-nosb');

  // 다시 넣기(고르기 대화상자 · 다른 공간 묶음 · 카탈로그 검색) → 새 시나리오 · 자유 항목
  await page.getByRole('button', { name: '+ 추가 · 변경' }).click();
  const dlg = page.getByRole('dialog', { name: /주차장 · 공간 제품 · 솔루션 고르기/ });
  await expect(dlg.getByText('다른 공간의 제품 · 솔루션', { exact: true })).toBeVisible();   // DSS 없이 만든 묶음의 고르기 묶음
  await dlg.locator('#wm-pick-search').fill('옥외형 사이니지 OHC55');
  await dlg.getByRole('checkbox', { name: /옥외형 사이니지 OHC55/ }).first().click();
  await dlg.getByRole('button', { name: '완료' }).click();
  await page.getByRole('button', { name: '+ 시나리오 추가' }).click();
  const c = page.locator('.ss-card').last();
  for (const [label, v] of [['시나리오 이름', '야간 주차 안내'], ['사용자', '야근 후 퇴근하는 임직원'], ['장면 1', '주차장 입구 사이니지에 빈 층이 뜸']]) {
    await c.getByRole('textbox', { name: label }).fill(v);
    await c.getByRole('textbox', { name: label }).press('Enter');
  }
  await c.getByRole('button', { name: '+ 쓰인 제품' }).click();
  await c.getByRole('option', { name: '옥외형 사이니지 OHC55' }).click();
  await c.getByRole('button', { name: '+ 시간대' }).click();
  await c.getByRole('textbox', { name: '시간대' }).fill('오후 9시 이후');
  await c.getByRole('textbox', { name: '시간대' }).press('Enter');
  await head.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: `${d.code} v1 저장했어요` })).toBeVisible({ timeout: 20_000 });
  await expect(head.locator('.cd-ref')).toHaveText(`${d.code} v1`);
  await expect(head.getByText('눌러서 바로 고쳐요')).toBeVisible();
  await shot(page, 'SC_View-nosb');
  const st = await (await request.get(`/api/scenario/v1/space-sets/${d.id}/stage`)).json();
  const park = st.stage.spaces.find((s: { name: string }) => s.name === '주차장');
  expect(park.scenarios[0].steps[0].product).toBe('옥외형 사이니지 OHC55');
  expect(park.scenarios[0].fields).toEqual([{ k: '시간대', v: '오후 9시 이후' }]);
  expect(st.stage.ver).toBe(1);
  expect(st.stage.from).toBeNull();
});
