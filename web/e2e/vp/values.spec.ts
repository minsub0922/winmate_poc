/**
 * 새 VP 흐름(2026-10-08 보드 webapp1 VP2 · VP2_AI · VP2_Pick · VP2_Detail · View content=vp) — 제품 · 솔루션마다 가치 여러 개 + 고객의 니즈.
 * 실제 스택(mock 모델). 화면 폭 · 칸 폭이 보드와 같은지(280 | 1fr · 본문 열 1180) 함께 본다.
 * 저장하면 완료 화면 없이 같은 주소의 보기(VP_View: 띠 h44 + 흰 판 · 줄 210 | 1fr) · 편집은 `?edit=1` · 목록 「열기」 · 새로고침도 보기.
 */
import { test, type Locator } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { expect, shot } from './helpers';

const w = async (l: Locator) => Math.round((await l.boundingBox())!.width);
const h = async (l: Locator) => Math.round((await l.boundingBox())!.height);

const CANDS = [
  { name: 'The Wall IAB 146"', kind: 'product', spaces: ['로비'] },
  { name: 'Flip Pro WA75D', kind: 'product', spaces: ['회의실'] },
  { name: 'MagicINFO', kind: 'solution', spaces: [] },
  { name: 'Smart Signage QB43C', kind: 'product', spaces: ['공용공간'] },
];

test('가치 · 고객의 니즈 — 고르기 · 직접 · AI 니즈 추론 · AI 가치 매칭 · 연결된 가치 · 저장 → 보기', async ({ page, request }) => {
  test.setTimeout(180_000);
  const title = `용산 오피스 가치 제안 ${tag()}`;
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });
  const dssRef = (await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.dss.ref as string;
  const r = await request.post('/api/vp/v1/value-maps', { data: { title, sb_id: sb.id, candidates: CANDS, context_text: '에너지 20% 절감 · 최초 AI Ready' } });
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

  // 모두 수락 → 저장 → 같은 주소의 보기(VP_View · 보드 View content=vp) — 「저장했어요」 같은 완료 안내는 없다
  await page.getByRole('button', { name: '모두 수락' }).click();
  await page.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByRole('heading', { name: title, level: 1 })).toBeVisible({ timeout: 20_000 });
  await expect(page).toHaveURL(new RegExp(`/vp/values/${d.id}$`));
  await expect(page.getByText(/저장했어요|완료됐|완성됐/)).toHaveCount(0);
  const saved = await (await request.get(`/api/vp/v1/value-maps/${d.id}`)).json();
  expect(saved).toMatchObject({ status: 'done', ver: 1 });
  const c = saved.counts as { items: number; values: number; needs: number };
  expect(c.items).toBe(3);
  await expect(page.locator('.fl-view__ref')).toHaveText(`${saved.code} v1`);
  await expect(page.locator('.fl-view__meta')).toHaveText(new RegExp(`^오늘 \\d{2}:\\d{2} 저장 · 제품 · 솔루션 3 · 가치 ${c.values} · 고객의 니즈 ${c.needs}/${c.values}$`));
  // 띠 — 어디서 몇 개 · 고르지 않은 것
  const strip = page.locator('.vpv-strip');
  await expect(strip).toHaveText(`${dssRef}에서 3개를 골랐어요· 고르지 않은 1 — Smart Signage QB43C`);
  // 흰 판 하나 · 고른 제품 · 솔루션마다 줄(수락한 가치만 · 점선 추천 없음)
  const rows = page.locator('.vpv-row');
  await expect(rows).toHaveCount(3);
  const wallRow = rows.filter({ hasText: 'The Wall IAB 146"' });
  await expect(wallRow.locator('.fl-vtag').first()).toHaveText('제품');
  await expect(wallRow.locator('.vpv-spaces')).toHaveText('로비');
  await expect(wallRow.locator('.vpv-count')).toHaveText('가치 2 · 니즈 2/2');
  const v1 = wallRow.locator('.vpv-val').filter({ hasText: '들어서는 순간 회사의 AI 비전을 보여 줌' });
  await expect(v1.locator('.vpv-space')).toHaveText('로비');
  await expect(v1.locator('.vpv-req')).toHaveText('RQ-01 최초 AI Ready');
  await expect(v1.locator('.vpv-need')).toContainText('고객의 니즈“방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요”직접');
  const v2 = wallRow.locator('.vpv-val').filter({ hasText: '사내 행사 때 로비를 무대로 바꿈' });
  await expect(v2.locator('.vpv-need')).toContainText('“행사 때마다 외부 장소를 빌리지 않았으면 해요”AI 추론 · 수락');
  await expect(rows.filter({ hasText: 'MagicINFO' }).locator('.fl-vtag').first()).toHaveText('솔루션');
  const shown = await page.locator('.vpv-val').count();
  expect(shown).toBe(c.values);
  await expect(page.locator('.vpv-need--empty')).toHaveCount(c.values - c.needs);
  if (c.values > c.needs) await expect(page.locator('.vpv-need--empty').first()).toContainText('비어 있어요 · 편집에서 적거나 AI 니즈 추론으로 채워요');
  // 보드 View: 본문 1100(1180 − 40 · 40) · 띠 h44 · 줄 왼쪽 210 | 오른쪽 1fr(1100 − 2 − 40 − 210 − 18 = 830) · 니즈 줄 ≥ 36 · 라벨 66 · 후속 작업 없음
  expect(await w(page.locator('.vpv-list'))).toBe(1100);
  expect(await h(strip)).toBe(44);
  expect(await w(page.locator('.vpv-item').first())).toBe(210);
  expect(await w(page.locator('.vpv-values').first())).toBe(830);
  expect(await h(page.locator('.vpv-need').first())).toBeGreaterThanOrEqual(36);
  expect(await w(page.locator('.vpv-need__label').first())).toBe(66);
  expect(await h(page.getByRole('link', { name: '편집' }))).toBe(38);
  await expect(page.locator('.fl-view__follow')).toHaveCount(0);
  await page.mouse.move(10, 890);
  await shot(page, 'VP_View-new');
  // flow.json — 이 콘텐츠(stages.vp) 강조
  await page.getByRole('button', { name: 'flow.json' }).click();
  const json = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(json.getByText('"vp": {').first()).toBeVisible();
  await expect(json.getByText('이 콘텐츠가 담긴 줄')).toBeVisible();
  await json.getByRole('button', { name: '닫기' }).last().click();

  // 편집 → ?edit=1 · 같은 맵 편집 화면(VP2)
  await page.getByRole('link', { name: '편집' }).click();
  await expect(page).toHaveURL(new RegExp(`/vp/values/${d.id}\\?edit=1$`));
  await expect(page.getByRole('heading', { name: '제품 · 솔루션마다 가치와 고객의 니즈를 적어요' })).toBeVisible();
  await expect(page.getByRole('button', { name: /The Wall IAB 146"/ })).toContainText('가치 2 · 니즈 2/2');
  // 목록에서 다시 열어도 같은 보기
  await page.getByRole('link', { name: '목록' }).click();
  await expect(page).toHaveURL(/\/vp$/);
  const row = page.locator('.fl-card').filter({ hasText: `${saved.code} v1` }).filter({ hasText: title });
  await expect(row).toBeVisible();
  await row.locator('.fl-cardtitle').click();
  await expect(page).toHaveURL(new RegExp(`/vp/values/${d.id}$`));
  await expect(page.getByRole('heading', { name: title, level: 1 })).toBeVisible();
  await expect(page.locator('.vv-need__input, .wm-flow__grid')).toHaveCount(0);
  await page.reload();
  await expect(page.locator('.vpv-row')).toHaveCount(3);
  await expect(page.getByText(/저장했어요|완료됐|완성됐/)).toHaveCount(0);
});
