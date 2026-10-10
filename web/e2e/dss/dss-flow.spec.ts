/**
 * 공간별 제품 매칭 DSS 새 흐름(2026-10-08 보드 webapp1 DS0 · DS1 · DS2 · DS2_AI · DS4 · DS4_AI · DS_Done) — 실제 스택(MODEL_MODE=mock ·
 * mocks/ai-tools/ds.industry_spaces.v1 · ds.solutions.v1 · KB 실데이터).
 * Storyboard(요구사항까지)를 API 로 만들고 → 목록 → Gate → DS2(공간 · 제품 직접 · AI 업종 · 공간 · 제품, 수락, 제품 고르기) → DS4(AI 솔루션 · 고르기 · 겹침 · 상세)
 * → 저장 → 완료(허브 stages.dss 확인). 보드의 고정 칸(270 · 816 · 940 · 465 · 1020 · 504)을 숫자로 재고 __screens__/<보드>-new.png 로 남긴다.
 * 실행: make e2e-feature SERVICE=dss (1 worker)
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { internalHeaders, shotTo, tag } from '../shell/flowkit';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '__screens__');
const shot = (page: Page, name: string) => shotTo(page, DIR, name);
const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { w: Math.round(b.width * 10) / 10, h: Math.round(b.height * 10) / 10, x: Math.round(b.x), y: Math.round(b.y) }; };
const w = async (l: Locator) => Math.round((await l.boundingBox())!.width);
const h = async (l: Locator) => Math.round((await l.boundingBox())!.height);

// 보드 DS2 예시(판교 스타트업 단지 · 요구사항까지) — mock 이 '입주사' 문장에 보드 답(업종 · 공간 추천)을 준다
const REQS = [
  { id: 'R1', text: '로비에서 입주사 안내와 입주사 공용 회의실 예약을 한 번에', status: 'ok', by: 'manual' },
  { id: 'R2', text: '반도체 박물관 협업 전시', status: 'ok', by: 'manual' },
  { id: 'R3', text: '단지 운영 · 단지 에너지 모니터링', status: 'check', by: 'manual' },
];

async function makePangyo(request: APIRequestContext, name: string) {
  const ref = `RQ-${tag()}`;
  const r = await request.post('/api/storyboard/v1/flows', {
    headers: internalHeaders('requirements'),
    data: { name, customer: 'G 공사', target: '단지운영본부장',
      rq: { ref, ver: 1, md: '- 고객사 G 공사 · 최종 제안대상 단지운영본부장\n- 요구 3 · 확인 필요 1',
        value: { customer: 'G 공사', title: name, target: '단지운영본부장', keymen: [], goals: [], requirements: REQS, counts: { keymen: 0, reqs: 3, check: 1 } },
        card: { title: name, facts: [['고객사', 'G 공사'], ['최종 제안대상', '단지운영본부장'], ['요구', '3 · 확인 필요 1']], groups: [], line: '요구 3 · 확인 필요 1' } } },
  });
  expect(r.ok(), await r.text()).toBeTruthy();
  return { ...(await r.json()) as { id: string; name: string }, ref };
}

test('DSS 새 흐름 — 목록 · Gate · 공간 · 제품 · AI · 솔루션 · 저장 · 허브 stages.dss', async ({ page, request }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `판교 스타트업 단지 ${tag()}`;
  const sb = await makePangyo(request, name);

  // DS0 — 목록(보드 List content=dss)
  await page.goto('/dss');
  await expect(page.getByRole('heading', { name: '공간별 제품 매칭 DSS', exact: true })).toBeVisible();
  await expect(page.getByText('Storyboard에 공간별 제품 · 솔루션을 골라 넣어요.')).toBeVisible();
  await expect(page.getByText('사전 작업 · Storyboard (고객 요구사항)')).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'DS0-new');
  await page.getByRole('link', { name: '새 DSS' }).first().click();

  // DS1 — 사전 작업 고르기(보드 Gate content=dss): 우리 Storyboard 를 고른다
  await expect(page).toHaveURL(/\/dss\/new$/);
  await expect(page.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  await expect(page.getByText('고객 요구사항이 연결된 Storyboard이 있어야 시작할 수 있어요.', { exact: false })).toBeVisible();
  const row = page.getByRole('radio', { name: new RegExp(name) });
  await row.click();
  await expect(row).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByText(`${name}에 DSS가 연결돼요`)).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'DS1-new');
  await page.getByRole('button', { name: '이 Storyboard로 시작' }).click();

  // DS2 — 공간 · 제품(빈 상태에서 직접 넣기)
  await expect(page).toHaveURL(/\/dss\/dss_[0-9A-Za-z]+$/, { timeout: 15_000 });
  const dssId = page.url().split('/').pop()!.split('?')[0];
  await expect(page.getByRole('heading', { name: '공간과 제품을 정해요' })).toBeVisible();
  await expect(page.locator('.wm-sbbar__chip')).toContainText(name);
  await expect(page.locator('.wm-sbbar__note')).toHaveText('DSS를 저장하면 이 Storyboard에 연결돼요');
  await expect(page.getByText('공간 0 · 제품 0')).toBeVisible();
  await expect(page.getByRole('button', { name: /업종\s*선택해 주세요/ })).toBeVisible();
  await page.locator('#ds-sp').fill('로비');
  await page.locator('#ds-sp').press('Enter');
  await expect(page.locator('[data-space="로비"]')).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('.ds-phead__line')).toHaveText(`근거 · ${sb.ref} 1 · 로비에서 입주사 안내와 입주…`);
  await expect(page.getByText('아직 제품이 없어요. 아래에서 모델명으로 찾아 넣거나, AI 자동 매칭을 써 보세요.')).toBeVisible();
  // 제품 검색(결과는 위로) → Smart Signage QM55C · 수량 2대
  await expect(page.locator('#ds-add')).toHaveAttribute('placeholder', '로비에 제품 추가 · 모델명이나 용도로 찾기');
  await page.locator('#ds-add').fill('QM55C');
  const res = page.getByRole('listbox', { name: '제품 검색 결과' });
  await expect(res.getByRole('option', { name: /Smart Signage QM55C/ })).toBeVisible({ timeout: 10_000 });
  await res.getByRole('option', { name: /Smart Signage QM55C/ }).click();
  const qm = page.locator('[data-product="Smart Signage QM55C"]');
  await expect(qm).toBeVisible();
  await expect(qm.locator('.ds-tag')).toHaveText('직접');
  await expect(qm.locator('.ds-qty')).toHaveText('[확인 필요]');
  await qm.locator('.ds-qty').click();
  await page.getByRole('textbox', { name: 'Smart Signage QM55C 수량' }).fill('2대');
  await page.getByRole('textbox', { name: 'Smart Signage QM55C 수량' }).press('Enter');
  await expect(qm.locator('.ds-qty')).toHaveText('2대');
  await page.locator('#ds-sp').fill('공용 회의실');
  await page.getByRole('button', { name: '추가', exact: true }).click();
  await expect(page.locator('[data-space="공용 회의실"]')).toHaveAttribute('aria-selected', 'true');
  await page.locator('[data-space="로비"]').click();
  await expect(page.getByText('공간 2 · 제품 1')).toBeVisible();
  // 보드 DS2 칸(1440 × 900): 본문 1180 · 공간 270 | 제품 816(1100 − 270 − 14) · 머리 47(46 + 선) · 제품 줄 68 · 아래 61 · 다음 48 · 업종 38 · AI 38 / 30
  expect(await w(page.locator('.wm-flow'))).toBe(1180);
  expect(await box(page.locator('.ds-spaces'))).toMatchObject({ w: 270, x: 300, y: 240, h: 582 });
  expect(await box(page.locator('.ds-prods'))).toMatchObject({ w: 816, x: 584, y: 240, h: 582 });
  expect(await box(page.locator('.ds-sphead'))).toMatchObject({ w: 268, h: 47 });
  expect(await box(page.locator('.ds-phead'))).toMatchObject({ w: 814, h: 47 });
  expect(await box(page.locator('.ds-sp').first())).toMatchObject({ w: 256, h: 44 });
  expect(await box(page.locator('.ds-spfoot'))).toMatchObject({ w: 268, h: 55 });
  expect(await box(page.locator('.ds-spadd'))).toMatchObject({ w: 248, h: 36 });
  expect(await box(qm)).toMatchObject({ w: 814, h: 68 });
  expect(await box(page.locator('.ds-pfoot'))).toMatchObject({ w: 814, h: 61 });
  expect(await box(page.locator('.ds-psearch'))).toMatchObject({ h: 38 });
  expect(await h(page.getByRole('button', { name: '제품 탐색에서 고르기' }))).toBe(38);
  expect(await h(page.getByRole('button', { name: /^업종/ }))).toBe(38);
  expect(await h(page.getByRole('button', { name: 'AI 업종 추론' }))).toBe(38);
  expect(await h(page.getByRole('button', { name: 'AI 공간 추천' }))).toBe(30);
  expect(await h(page.getByRole('button', { name: 'AI 공간별 제품 자동 매칭' }))).toBe(30);
  expect(await box(page.getByRole('button', { name: '다음 · 솔루션' }))).toMatchObject({ h: 48, y: 834 });
  expect(await h(qm.getByRole('button', { name: '상세' }))).toBe(32);
  expect(await h(qm.locator('.ds-qty'))).toBe(28);
  await page.mouse.move(10, 890);
  await shot(page, 'DS2-new');

  // DS2_AI — AI 업종 추론(점선 줄 · 적용 전) · AI 공간 추천(점선 · 추가) · AI 공간별 제품 자동 매칭(점선 · 수락)
  await page.getByRole('button', { name: 'AI 업종 추론' }).click();
  const indAi = page.getByRole('status', { name: 'AI 업종 추론' });
  await expect(indAi).toContainText('오피스 · 업무시설', { timeout: 20_000 });
  await expect(indAi).toContainText(`근거 · ${sb.ref} ‘입주사 공용 회의실 예약’ · ‘단지 운영’ — 복합단지일 수도 있어요`);
  await page.getByRole('button', { name: 'AI 공간 추천' }).click();
  await expect(page.locator('[data-rec]')).toHaveCount(5, { timeout: 20_000 });
  await expect(page.locator('[data-rec]')).toHaveText([/라운지/, /전시 공간/, /통합 관제실/, /공용 공간/, /주차장\s*확장/]);
  await expect(page.locator('[data-rec="전시 공간"] .ds-rec__why')).toHaveText(`${sb.ref} 반도체 박물관 협업 전시`);
  await page.getByRole('button', { name: 'AI 공간별 제품 자동 매칭' }).click();
  await expect(page.locator('[data-by="ai-pending"]').first()).toBeVisible({ timeout: 30_000 });
  const pendLobby = await page.locator('[data-by="ai-pending"]').count();
  expect(pendLobby).toBeGreaterThan(0);
  await expect(page.locator('[data-space="로비"] .ds-sp__pend')).toHaveText(`+${pendLobby}`);
  await expect(page.locator('[data-space="공용 회의실"] .ds-sp__pend')).toBeVisible();
  await expect(page.getByText('수락하지 않은 추천은 저장되지 않아요')).toBeVisible();
  await expect(page.locator('[data-by="ai-pending"] .ds-tag').first()).toHaveText('AI 추천');
  await expect(page.locator('[data-by="ai-pending"] .ds-qty').first()).toHaveText('[확인 필요]');
  const acceptAll = page.getByRole('button', { name: /^추천 모두 수락 \d+$/ });
  await expect(acceptAll).toBeVisible();
  // 보드 DS2_AI(앱과 같은 Noto Sans KR 로 잰 값): 업종 줄 1100 × 40 · 그리드가 12 아래로(292) · 추천 공간 줄 256 × 46(두 줄 글자 36 + 4 · 4) · 점선 제품 줄 69(위 선 1)
  expect(await box(indAi)).toMatchObject({ w: 1100, h: 40, y: 240 });
  expect(await box(page.locator('.ds-spaces'))).toMatchObject({ y: 292, h: 530 });
  expect(await box(page.locator('[data-rec]').first())).toMatchObject({ w: 256, h: 46 });
  expect(await box(page.locator('[data-by="ai-pending"]').first())).toMatchObject({ w: 814, h: 69 });
  expect(await h(page.locator('[data-rec] .ds-rec__add').first())).toBe(28);
  await page.mouse.move(10, 890);
  await shot(page, 'DS2_AI-new');

  // 적용 · 수락 — 업종(ai-accepted), 로비 첫 추천 수락, 나머지 모두 수락
  await indAi.getByRole('button', { name: '적용' }).click();
  await expect(indAi).toHaveCount(0);
  await expect(page.getByRole('button', { name: /^업종\s*오피스 · 업무시설/ })).toBeVisible();
  const firstPend = page.locator('[data-by="ai-pending"]').first();
  const firstName = (await firstPend.getAttribute('data-product'))!;
  await firstPend.getByRole('button', { name: '수락' }).click();
  await expect(page.locator(`[data-product="${firstName}"]`)).toHaveAttribute('data-by', 'ai-accepted');
  await expect(page.locator(`[data-product="${firstName}"] .ds-tag`)).toHaveText('AI 추천 · 수락');
  await page.getByRole('button', { name: /^추천 모두 수락 \d+$/ }).click();
  await expect(page.locator('[data-by="ai-pending"]')).toHaveCount(0);
  await expect(page.getByText('수락하지 않은 추천은 저장되지 않아요')).toHaveCount(0);
  // 추천 공간 추가 → 근거 유지(ai-accepted) · 바로 고른다
  await page.getByRole('button', { name: '전시 공간 공간 추가' }).click();
  await expect(page.locator('[data-space="전시 공간"]')).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('.ds-phead__line')).toHaveText(`근거 · ${sb.ref} 2 · 반도체 박물관 협업 전시`);
  await expect(page.locator('[data-rec]')).toHaveCount(4);
  // 제품 탐색에서 고르기(ProdPicker 760×640) — 카탈로그 검색으로 The Wall 하나 · 직접 추가 하나
  await page.getByRole('button', { name: '제품 탐색에서 고르기' }).click();
  const picker = page.getByRole('dialog', { name: '전시 공간에 넣을 제품 고르기' });
  await expect(picker).toBeVisible();
  expect(await box(picker)).toMatchObject({ w: 760, h: 640 });
  await picker.locator('#wm-pick-search').fill('The Wall');
  await picker.getByRole('checkbox', { name: /실내용 The Wall IWC 카탈로그 · / }).click();
  // 셸 ProdPicker 는 고른 카탈로그 항목을 「고른 카탈로그 항목」과 검색 결과에 함께 보인다(둘 다 체크)
  await expect(picker.getByRole('checkbox', { name: /실내용 The Wall IWC/ }).first()).toHaveAttribute('aria-checked', 'true');
  await picker.locator('#wm-pick-search').fill('협업 전시 미디어월');
  await picker.getByRole('checkbox', { name: /협업 전시 미디어월.*직접 추가 · KB 에 없음 · 확인 필요/ }).last().click();
  await expect(picker.getByText('2개 골랐어요')).toBeVisible();
  await picker.getByRole('button', { name: '완료' }).click();
  await expect(page.locator('[data-product="실내용 The Wall IWC"] .ds-pwhy')).toHaveText('직접 추가');
  await expect(page.locator('[data-product="협업 전시 미디어월"] .ds-pwhy')).toHaveText('직접 추가 · KB 에 없음 · 확인 필요');
  // 빼기
  await page.getByRole('button', { name: '협업 전시 미디어월 빼기' }).click();
  await expect(page.locator('[data-product="협업 전시 미디어월"]')).toHaveCount(0);
  // 상세 → 셸 제품 상세 시트(모델코드 있는 제품)
  await page.locator('[data-space="로비"]').click();
  await qm.getByRole('button', { name: '상세' }).click();
  await expect(page).toHaveURL(/detail=product%3ALH55QMCEBGCXKR|detail=product:LH55QMCEBGCXKR/);
  await expect(page.getByRole('button', { name: '✓ 추가됨' })).toBeVisible({ timeout: 10_000 });   // 셸 시트: 이미 이 DSS 에 있는 제품
  await page.keyboard.press('Escape');
  await expect(page).not.toHaveURL(/detail=/);

  const doc = await (await request.get(`/api/dss/v1/dss/${dssId}`)).json();
  const nProducts = doc.counts.products as number;
  expect(doc.counts).toMatchObject({ spaces: 3, pending: 4 });           // 남은 추천 공간 4개는 대기(저장에 안 들어간다)
  expect(doc.industry).toMatchObject({ value: '오피스 · 업무시설', by: 'ai-accepted' });

  // DS4 — 솔루션(0개 이상 · 본문 940 · 카드 465)
  await page.getByRole('button', { name: '다음 · 솔루션' }).click();
  await expect(page).toHaveURL(/step=solution/);
  await expect(page.getByRole('heading', { name: '솔루션을 고르세요 · 0개 이상' })).toBeVisible();
  await expect(page.getByText('고르지 않아도 저장할 수 있어요.')).toBeVisible();
  await expect(page.locator('.wm-sbbar__note')).toHaveText(`공간 3 · 제품 ${nProducts}`);
  await expect(page.locator('[data-solution="magicinfo"]')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('솔루션 없이 저장해도 돼요')).toBeVisible();
  // 보드 DS4(Noto Sans KR): 머리 940 × 57(h1 34 + 4 + 19) · 카드 그리드 y263 · 카드 465 · 최소 112
  expect(await box(page.locator('.ds-solhead'))).toMatchObject({ w: 940, x: 380, y: 194, h: 57 });
  expect(await box(page.locator('.ds-solgrid'))).toMatchObject({ w: 940, x: 380, y: 263 });
  expect(await w(page.locator('[data-solution]').first())).toBe(465);
  expect(await h(page.getByRole('button', { name: 'AI 솔루션 추천' }))).toBe(38);
  expect(await h(page.getByRole('button', { name: 'DSS 저장' }))).toBe(48);
  expect(await h(page.locator('[data-solution="magicinfo"]').getByRole('button', { name: 'MagicINFO 상세' }))).toBe(32);
  await expect(page.locator('[data-solution="magicinfo"] .ds-sollinks')).toContainText('함께 쓰는 제품 · ');
  await page.mouse.move(10, 890);
  await shot(page, 'DS4-new');

  // DS4_AI — AI 솔루션 추천(mock: MagicINFO · SmartThings Pro · b.IoT) → 점선 · AI 추천 · 근거
  await page.getByRole('button', { name: 'AI 솔루션 추천' }).click();
  await expect(page.locator('.ds-sol--rec')).toHaveCount(3, { timeout: 20_000 });
  const recIds = await page.locator('.ds-sol--rec').evaluateAll((els) => els.map((e) => e.getAttribute('data-solution')));
  expect(recIds).toEqual(['magicinfo', 'smartthings_pro', 'biot']);
  await expect(page.locator('[data-solution="magicinfo"] .ds-solwhy')).toHaveText(`근거 · ${sb.ref} 1 입주사 안내 · 사이니지`);
  await expect(page.locator('[data-solution="biot"] .ds-tag')).toHaveText('AI 추천');
  await page.mouse.move(10, 890);
  await shot(page, 'DS4_AI-new');

  // 고르기 — MagicINFO + VXT 는 겹침 안내(보드 DS4) → VXT 빼고 SmartThings Pro · b.IoT
  await page.locator('[data-solution="magicinfo"]').getByRole('checkbox').click();
  await expect(page.locator('[data-solution="magicinfo"]')).toHaveClass(/ds-sol--on/);
  await expect(page.locator('[data-solution="magicinfo"] .ds-tag')).toHaveText('AI 추천 · 수락');
  await page.locator('[data-solution="vxt"]').getByRole('checkbox').click();
  const overlap = page.locator('.ds-overlap');
  await expect(overlap).toHaveText('MagicINFO와 Samsung VXT는 둘 다 사이니지 CMS예요. 같은 사이니지에 함께 쓰는 경우는 드물어요.');
  expect(await box(overlap)).toMatchObject({ w: 940, h: 38 });
  await expect(page.getByText('솔루션 2개 선택')).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'DS4-overlap-new');
  await page.locator('[data-solution="vxt"]').getByRole('checkbox').click();
  await expect(overlap).toHaveCount(0);
  await page.locator('[data-solution="smartthings_pro"]').getByRole('checkbox').click();
  await expect(page.locator('[data-solution="smartthings_pro"]')).toHaveClass(/ds-sol--on/);
  await page.locator('[data-solution="biot"]').getByRole('checkbox').click();
  await expect(page.getByText('솔루션 3개 선택')).toBeVisible();
  // 나머지 솔루션 펼치기 → 카드 칸 안에서만 스크롤 · 아래 줄은 그대로(보드 y830)
  const more = page.getByRole('button', { name: /^솔루션 \d+개 더 보기$/ });
  if (await more.count()) {
    await more.click();
    expect(await page.locator('[data-solution]').count()).toBeGreaterThan(5);
    expect(await page.locator('.ds-solscroll').evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
    await page.getByRole('button', { name: '관련 있는 솔루션만 보기' }).click();
  }
  expect(await box(page.getByRole('button', { name: 'DSS 저장' }))).toMatchObject({ y: 830, h: 48 });
  // 상세 → 셸 솔루션 상세 시트(보드 SolutionDetail)
  await page.locator('[data-solution="magicinfo"]').getByRole('button', { name: 'MagicINFO 상세' }).click();
  await expect(page).toHaveURL(/detail=solution(%3A|:)magicinfo/);
  await expect(page.getByRole('dialog').filter({ hasText: 'MagicINFO' }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: '✓ 추가됨' })).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'DS4-detail-new');
  await page.keyboard.press('Escape');
  await expect(page).not.toHaveURL(/detail=/);
  // 셸 솔루션 시트의 「현재 작업에 추가」 → 고른 솔루션에 더해진다(겹침 안내) → 다시 빼기
  await page.locator('[data-solution="vxt"]').getByRole('button', { name: 'Samsung VXT 상세' }).click();
  await page.getByRole('button', { name: '현재 작업에 추가' }).click();
  await expect(page.getByRole('button', { name: '✓ 추가됨' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('[data-solution="vxt"]')).toHaveClass(/ds-sol--on/);
  await expect(overlap).toBeVisible();
  await page.locator('[data-solution="vxt"]').getByRole('checkbox').click();
  await expect(overlap).toHaveCount(0);
  await expect(page.getByText('솔루션 3개 선택')).toBeVisible();

  // 저장 → DS_Done(보드 Done content=dss)
  await page.getByRole('button', { name: 'DSS 저장' }).click();
  await expect(page.getByRole('heading', { name: 'DSS를 저장했어요' })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(`공간 3 · 제품 ${nProducts} · 솔루션 3을 Storyboard에 담았어요`)).toBeVisible();
  await expect(page.getByText(/"stages\.dss": \{/)).toBeVisible();
  await expect(page.locator('.wm-done__md pre')).toContainText('- 업종: 오피스 · 업무시설 · 공간 3');
  await expect(page.locator('.wm-done__md pre')).toContainText('- 솔루션: MagicINFO · SmartThings Pro · b.IoT');
  await expect(page.locator('.wm-done__md pre')).toContainText('Smart Signage QM55C ×2');
  const follows = page.locator('a.wm-follow');
  await expect(follows).toHaveCount(2);
  await expect(follows.nth(0)).toHaveAttribute('href', `/scenario/new?sb=${sb.id}&auto=1`);
  await expect(follows.nth(0)).toContainText('공간 시나리오 생성');
  await expect(follows.nth(0)).toContainText('공간 3개에서 사용자가 겪는 장면을 만들어요');
  await expect(follows.nth(1)).toHaveAttribute('href', `/spec/new?sb=${sb.id}&auto=1`);
  await expect(follows.nth(1)).toContainText(`매칭한 제품 ${nProducts}개를 스펙 시트로`);
  await expect(page.locator('.wm-sbbar__stage').first()).toHaveText('DSS까지');
  // 보드 Done: 카드 1020 · 요약 · JSON 상자 250 · 후속 작업 2칸 504 × 84(간격 12)
  expect(await w(page.locator('.wm-done__card'))).toBe(1020);
  expect(await h(page.locator('.wm-done__md'))).toBe(250);
  expect(await box(follows.nth(0))).toMatchObject({ w: 504, h: 84, x: 340 });
  expect(await box(follows.nth(1))).toMatchObject({ w: 504, h: 84, x: 856 });

  // 허브 flow.json stages.dss — §6 계약 모양(점선 대기 값은 빠진다)
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const st = flow.stages.dss;
  expect(st.ref).toMatch(/^DSS-\d+$/);
  expect(st.ver).toBe(1);
  expect(st.industry).toMatchObject({ value: '오피스 · 업무시설', by: 'ai-accepted' });
  expect(st.spaces.map((s: { name: string }) => s.name)).toEqual(['로비', '공용 회의실', '전시 공간']);
  expect(st.spaces[2]).toMatchObject({ by: 'ai-accepted', basis: `${sb.ref} 2 · 반도체 박물관 협업 전시` });
  expect(st.spaces[0].products[0]).toMatchObject({ name: 'Smart Signage QM55C', kind: 'product', ref: 'kb:model:mdl_LH55QMCEBGCXKR', qty: '2대', by: 'manual' });
  expect(st.spaces.flatMap((s: { products: Array<{ by: string }> }) => s.products).every((p: { by: string }) => p.by !== 'ai-pending')).toBe(true);
  expect(st.solutions.map((s: { name: string; by: string }) => [s.name, s.by])).toEqual([['MagicINFO', 'ai-accepted'], ['SmartThings Pro', 'ai-accepted'], ['b.IoT', 'ai-accepted']]);
  expect(st.counts).toEqual({ spaces: 3, products: nProducts, solutions: 3 });
  const cell = flow.cells.find((c: { key: string }) => c.key === 'dss');
  expect(cell).toMatchObject({ state: 'done', ref: st.ref, route: `/dss/${dssId}` });
  await page.mouse.move(10, 890);
  await shot(page, 'DS_Done-new');
  await page.getByRole('button', { name: '전체 JSON 보기' }).click();
  const dlg = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByText('"dss": {').first()).toBeVisible();
  await shot(page, 'DS_DoneJson-new');
  await dlg.getByRole('button', { name: '닫기' }).last().click();

  // 다시 고치기 → DS2 · 목록에 저장된 줄(DSS-nn v1) · Gate 는 「DSS-nn v1 있음」
  await page.getByRole('button', { name: '다시 고치기' }).click();
  await expect(page.getByRole('heading', { name: '공간과 제품을 정해요' })).toBeVisible();
  await expect(page).not.toHaveURL(/step=solution/);
  await page.goto('/dss');
  const listRow = page.getByRole('row').filter({ hasText: name });
  await expect(listRow).toContainText(`${st.ref} v1`);
  await expect(listRow.getByRole('link', { name: '열기' })).toHaveAttribute('href', `/dss/${dssId}`);
  await page.goto('/dss/new');
  await expect(page.getByRole('radio', { name: new RegExp(name) })).toContainText(`${st.ref} v1 있음`);
});

test('DSS — Storyboard 화면의 「만들기」(?sb=&auto=1)는 Gate 를 건너뛰고 바로 DS2', async ({ page, request }) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makePangyo(request, `판교 바로 만들기 ${tag()}`);
  await page.goto(`/dss/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/dss\/dss_[0-9A-Za-z]+$/, { timeout: 15_000 });
  await expect(page.getByRole('heading', { name: '공간과 제품을 정해요' })).toBeVisible();
  await expect(page.locator('.wm-sbbar__chip')).toContainText(sb.name);
  // 1920 × 1080: 본문 열은 1180 가운데 · 공간 270 | 제품 816 · 그리드가 높이를 채운다(1080 − 64 − 56 − 52 − 36 − 38 − 12 − 12 − 48 = 762)
  await page.setViewportSize({ width: 1920, height: 1080 });
  expect(await w(page.locator('.wm-flow'))).toBe(1180);
  expect(await box(page.locator('.ds-spaces'))).toMatchObject({ w: 270, h: 762 });
  expect(await box(page.locator('.ds-prods'))).toMatchObject({ w: 816, h: 762 });
  await page.setViewportSize({ width: 1440, height: 900 });
  // 업종 고르기(220 목록 · 8개 · 보드 순서)
  await page.getByRole('button', { name: /^업종/ }).click();
  const menu = page.getByRole('listbox', { name: '업종' });
  await expect(menu.getByRole('option')).toHaveText(['오피스 · 업무시설', '리테일', '외식 · 카페', '호텔 · 숙박', '병원 · 헬스케어', '교육', '공공 · 관공서', '주거 · 복합단지']);
  expect(await box(menu)).toMatchObject({ w: 220 });
  expect(await h(menu.getByRole('option').first())).toBe(34);
  await menu.getByRole('option', { name: '교육' }).click();
  await expect(menu).toHaveCount(0);
  await expect(page.getByRole('button', { name: /^업종\s*교육/ })).toHaveClass(/ds-indbtn--set/);
  // 공간 빼기(손을 올리면 개수 자리에 ×)
  await page.locator('#ds-sp').fill('카페');
  await page.locator('#ds-sp').press('Enter');
  await expect(page.locator('[data-space="카페"]')).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('.ds-phead__line')).toHaveText('직접 추가한 공간');
  await page.locator('[data-space="카페"]').hover();
  await page.getByRole('button', { name: '카페 공간 빼기' }).click();
  await expect(page.locator('[data-space="카페"]')).toHaveCount(0);
  await expect(page.getByText('먼저 공간을 넣어 주세요.', { exact: false })).toBeVisible();
  // 공간 · 제품 없이 솔루션으로 가면 저장이 막힌다(주황 안내)
  await page.getByRole('button', { name: '다음 · 솔루션' }).click();
  await expect(page.getByText('공간에 제품을 하나 이상 넣어야 저장할 수 있어요')).toBeVisible();
  await expect(page.getByRole('button', { name: 'DSS 저장' })).toBeDisabled();
  await page.getByRole('button', { name: '공간 · 제품' }).click();
  await expect(page.getByRole('heading', { name: '공간과 제품을 정해요' })).toBeVisible();
});
