/**
 * 새 VP 흐름(2026-10-08 보드 webapp1 VP2 · VP2_AI · VP2_Pick · VP2_Detail · VP_Done) — 제품 · 솔루션마다 가치 여러 개 + 고객의 니즈.
 * 실제 스택(mock 모델). 화면 폭 · 칸 폭이 보드와 같은지(280 | 1fr · 본문 열 1180) 함께 본다.
 */
import { test } from '@playwright/test';
import { expect, shot } from './helpers';

const CANDS = [
  { name: 'The Wall IAB 146"', kind: 'product', spaces: ['로비'] },
  { name: 'Flip Pro WA75D', kind: 'product', spaces: ['회의실'] },
  { name: 'MagicINFO', kind: 'solution', spaces: [] },
  { name: 'Smart Signage QB43C', kind: 'product', spaces: ['공용공간'] },
];

test('가치 · 고객의 니즈 — 고르기 · 직접 · AI 니즈 추론 · AI 가치 매칭 · 연결된 가치 · 저장', async ({ page, request }) => {
  test.setTimeout(180_000);
  const r = await request.post('/api/vp/v1/value-maps', { data: { title: '용산 AI Ready 오피스', sb_id: 'SB-01', candidates: CANDS, context_text: '에너지 20% 절감 · 최초 AI Ready' } });
  expect(r.status()).toBe(201);
  const d = await r.json();
  const wall = d.items[0].key;
  await request.post(`/api/vp/v1/value-maps/${d.id}/items/${wall}/values`, { data: { space: '로비', message: '들어서는 순간 회사의 AI 비전을 보여 줌', need: '방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요', req: 'RQ-01 최초 AI Ready' } });
  await request.post(`/api/vp/v1/value-maps/${d.id}/items/${wall}/values`, { data: { space: '로비', message: '사내 행사 때 로비를 무대로 바꿈' } });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/vp/values/${d.id}`);
  await expect(page.getByRole('heading', { name: '제품 · 솔루션마다 가치와 고객의 니즈를 적어요' })).toBeVisible();
  // 보드 VP2: 왼쪽 280 · 본문 열 1180(사이드바 260 오른쪽)
  const left = page.locator('.wm-flow__grid > .wm-flow__panel').first();
  expect(Math.round((await left.boundingBox())!.width)).toBe(280);
  expect(Math.round((await page.locator('.wm-flow').boundingBox())!.width)).toBe(1180);
  await expect(page.getByRole('button', { name: /The Wall IAB 146"/ })).toContainText('가치 2 · 니즈 1/2');
  await shot(page, 'VP2-new');

  // AI 니즈 추론(mock: '행사' → 고정 문장) → 점선 → 수락
  await page.getByRole('button', { name: 'AI 니즈 추론' }).click();
  await expect(page.getByText('“행사 때마다 외부 장소를 빌리지 않았으면 해요”')).toBeVisible();
  await page.locator('.vv-need').getByRole('button', { name: '수락' }).click();
  await expect(page.getByRole('button', { name: /The Wall IAB 146"/ })).toContainText('가치 2 · 니즈 2/2');

  // AI 가치 매칭 추천(mock 은 LLM 없이 KB 원문 메시지 → 점선 후보)
  await page.getByRole('button', { name: /AI 가치 매칭 추천/ }).click();
  await expect(page.getByRole('status').filter({ hasText: '점선은 수락해야 들어가요' })).toBeVisible();
  await page.getByRole('button', { name: /MagicINFO/ }).first().click();
  await expect(page.locator('.vv-card--pend').first()).toBeVisible();
  await shot(page, 'VP2_AI-new');

  // 제품 · 솔루션 고르기 — QB43C 빼기
  await page.getByRole('button', { name: /제품 · 솔루션 고르기 · 4/ }).click();
  const dlg = page.getByRole('dialog', { name: 'VP에 넣을 제품 · 솔루션 고르기' });
  await expect(dlg).toBeVisible();
  await dlg.getByRole('checkbox', { name: /Smart Signage QB43C/ }).click();
  await expect(dlg.getByText('3개 골랐어요')).toBeVisible();
  await shot(page, 'VP2_Pick-new');
  await dlg.getByRole('button', { name: '완료' }).click();
  await expect(page.getByRole('button', { name: /제품 · 솔루션 고르기 · 3/ })).toBeVisible();

  // 연결된 가치 전체 — KB 공식 메시지
  await page.getByRole('button', { name: /연결된 가치 전체 보기/ }).click();
  const det = page.getByRole('dialog', { name: /MagicINFO.*연결된 가치/ });
  await expect(det.getByText('삼성 공식 메시지')).toBeVisible();
  await shot(page, 'VP2_Detail-new');
  await det.getByRole('button', { name: '닫기' }).last().click();

  // 모두 수락 → 저장 → 완료(flow.json stages.vp)
  await page.getByRole('button', { name: '모두 수락' }).click();
  await page.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByRole('heading', { name: '가치 제안을 저장했어요' })).toBeVisible();
  await expect(page.getByText(/"stages\.vp": \{/)).toBeVisible();
  await shot(page, 'VP_Done-new');
});
