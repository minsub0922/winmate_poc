/**
 * 공간별 제품 매칭 DSS(보드 webapp1 v63 DS0 · DS1 · DS2 · DS2_AI · DS4 · DS4_AI · DS_View · DS_ViewJson · DS2_Edit) — 실제 스택(MODEL_MODE=mock ·
 * mocks/ai-tools/ds.industry_spaces.v1 · ds.solutions.v1 · KB 실데이터).
 * Storyboard(요구사항까지)를 API 로 만들고 → 목록 → 「새 DSS 만들기」 → 목록 위 팝업에서 Storyboard 고르기 → 상세 한 장(새로 만들기 DS2) → 바로 입력
 * → AI(업종 · 공간 · 공간별 제품, 점선 · 수락, DS2_AI) → 솔루션 고르기 팝업(DS4 · DS4_AI · 겹침) → 저장 → 같은 화면이 저장됨(DS_View · flow.json)
 * → 수량 하나 고치기 → 「고친 곳 1」(DS2_Edit) → 되돌리기 → 다시 고쳐 저장 · v2. 보드 고정 칸(1180 · 1100 · 2.2fr · 카드 4열 · 수량 60 · 칩 236 · 팝업 820×700)을
 * 숫자로 재고 __screens__/<보드>.png 로 남긴다(_rendered/webapp1/<보드>.jpg 와 나란히 본다).
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

/** 공간 카드 · 그 안의 제품 줄 · 수량 칸 */
const card = (page: Page, name: string) => page.locator(`[data-space-card="${name}"]`);
const prow = (page: Page, space: string, product: string) => card(page, space).locator(`[data-product="${product}"]`);
const qty = (page: Page, product: string) => page.getByRole('textbox', { name: `${product} 수량`, exact: true });

test('DSS — 목록 · 팝업 · 상세 한 장(새로 만들기 → AI → 솔루션 팝업 → 저장 → 고친 곳 → 되돌리기 → v2)', async ({ page, request }) => {
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `판교 스타트업 단지 ${tag()}`;
  const sb = await makePangyo(request, name);

  // DS0 — 목록(보드 List content=dss) → 「새 DSS 만들기」
  await page.goto('/dss');
  await expect(page.getByRole('heading', { name: '공간별 제품 매칭 DSS', exact: true })).toBeVisible();
  await page.getByRole('link', { name: /새 DSS 만들기/ }).first().click();

  // DS1 — 목록 위 팝업(보드 Gate 880 × 780)에서 우리 Storyboard 를 고른다
  await expect(page).toHaveURL(/\/dss\/new$/);
  const gate = page.getByRole('dialog', { name: '새 DSS 만들기 · Storyboard 고르기' });
  await expect(gate).toBeVisible();
  expect(await box(gate)).toMatchObject({ w: 880, h: 780 });
  const row = gate.getByRole('radio', { name: new RegExp(name) });
  await row.click();
  await expect(row).toHaveAttribute('aria-checked', 'true');
  await page.mouse.move(10, 890);
  await shot(page, 'DS1');
  await gate.getByRole('button', { name: '이 Storyboard로 시작' }).click();

  // DS2 — 상세 한 장(새로 만들기): 머리 · 요약 칸 · 공간 · 제품 · 솔루션 띠. 단계 · 완료 화면 없음
  await expect(page).toHaveURL(/\/dss\/dss_[0-9A-Za-z]+$/, { timeout: 15_000 });
  const dssId = page.url().split('/').pop()!.split('?')[0];
  const head = page.locator('.cd-head');
  await expect(head.getByRole('heading', { name, exact: true })).toBeVisible();
  await expect(head.locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(head.locator('.cd-meta')).toHaveText(`새로 만드는 중 · 쓰는 대로 작성 중으로 남아요 · 저장하면 ${sb.id}에 연결돼요`);
  await expect(page.locator('.wm-sbbar__chip')).toContainText(name);
  await expect(page.locator('.wm-sbbar__note')).toHaveText('저장하면 이 Storyboard에 연결돼요 · 사전 작업에서 골랐어요');
  await expect(page.getByRole('button', { name: '업종 선택해 주세요' })).toBeVisible();
  await expect(page.locator('.ds-ind__k')).toHaveText('업종 · 목록에서 고르거나 AI 업종 추론');
  await expect(page.locator('.ds-fact').nth(2)).toHaveText('솔루션00개도 돼요');
  await expect(page.locator('.ds-sols')).toContainText('솔루션 0고르지 않아도 저장돼요');
  await expect(page.getByRole('button', { name: /^저장$/ })).toBeVisible();
  // 공간 · 제품 직접 — 「+ 공간 추가」 칸에 이름 → 카드 · 근거
  await page.locator('#ds-add-space').fill('로비');
  await page.locator('#ds-add-space').press('Enter');
  await expect(card(page, '로비')).toBeVisible();
  await expect(card(page, '로비').locator('.ds-sp__basis')).toHaveText(`근거 · ${sb.ref} 1 · 로비에서 입주사 안내와 입주…`);
  await page.locator('#ds-add-space').fill('공용 회의실');
  await page.locator('#ds-add-space').press('Enter');
  await expect(card(page, '공용 회의실').locator('.ds-sp__basis')).toHaveText(`근거 · ${sb.ref} 1 · 공용 회의실 예약을 한 번에`);
  // 머리가 「작성 중」으로(무언가 썼다) — 저장 전 상세는 같은 화면
  await expect(head.locator('.cd-ref')).toHaveText('새로 만들기');
  // + 제품 → 카드 안 찾기 칸 → QM55C → 수량 칸(60 · 비면 주황) → 2대
  await card(page, '로비').getByRole('button', { name: '로비에 제품 추가' }).click();
  const find = page.getByRole('combobox', { name: '로비에 제품 추가' });
  await expect(find).toBeFocused();
  await find.fill('QM55C');
  const res = page.getByRole('listbox', { name: '로비 제품 찾기 결과' });
  await expect(res.getByRole('option', { name: /Smart Signage QM55C/ }).first()).toBeVisible({ timeout: 10_000 });
  await res.getByRole('option', { name: /Smart Signage QM55C/ }).first().click();
  const qm = prow(page, '로비', 'Smart Signage QM55C');
  await expect(qm).toBeVisible();
  await expect(qm.locator('.ds-by')).toHaveText('직접');
  await expect(qty(page, 'Smart Signage QM55C')).toHaveClass(/ds-qty--warn/);
  await page.keyboard.press('Escape');
  await expect(find).toHaveCount(0);
  await qty(page, 'Smart Signage QM55C').fill('2대');
  await qty(page, 'Smart Signage QM55C').press('Enter');
  await expect(qty(page, 'Smart Signage QM55C')).toHaveClass(/ds-qty--set/);
  await expect(page.locator('.ds-fact').nth(1)).toHaveText('제품1');
  await expect(card(page, '로비').locator('.ds-sp__n')).toHaveText('제품 1');
  await expect.poll(async () => (await (await request.get(`/api/dss/v1/dss/${dssId}`)).json()).spaces[0].products[0].qty).toBe('2대');
  // 보드 DS2(1440 × 900): 본문 1180 · 안쪽 1100 · 머리 46 · 저장 42 · 요약 칸 62(업종 2.2fr = (1100 − 36) × 2.2 / 5.2 ≈ 450.2 · 나머지 204.6) · 머리 줄 32 · AI 32 · 카드 4열(266) · 수량 60 × 24 · 띠 56
  expect(await w(page.locator('.wm-flow'))).toBe(1180);
  expect(await box(page.locator('.ds-body'))).toMatchObject({ w: 1100, x: 300 });
  expect(await box(head)).toMatchObject({ w: 1100, h: 46, y: 136 });
  expect(await h(page.getByRole('button', { name: /^저장$/ }))).toBe(42);
  expect(await box(page.locator('.ds-ind'))).toMatchObject({ h: 62, y: 196 });
  expect(Math.abs((await box(page.locator('.ds-ind'))).w - 1064 * 2.2 / 5.2)).toBeLessThan(0.5);
  expect(Math.abs((await box(page.locator('.ds-fact').first())).w - 1064 / 5.2)).toBeLessThan(0.5);
  expect(await h(page.locator('.ds-fact').first())).toBe(62);
  expect(await box(page.locator('.ds-sechead'))).toMatchObject({ h: 32, y: 268 });
  expect(await h(page.getByRole('button', { name: 'AI 공간 추천' }))).toBe(32);
  expect(await h(page.getByRole('button', { name: 'AI 업종 추론' }))).toBe(32);
  expect(await h(page.getByRole('button', { name: '업종 선택해 주세요' }))).toBe(34);
  expect(await box(card(page, '로비'))).toMatchObject({ w: 266, x: 300, y: 310 });
  expect(await box(card(page, '공용 회의실'))).toMatchObject({ w: 266, x: 578 });
  expect(await box(page.locator('.ds-spadd'))).toMatchObject({ w: 266, x: 856, h: 120 });
  expect(await box(qty(page, 'Smart Signage QM55C'))).toMatchObject({ w: 60, h: 24 });
  expect(await box(qm)).toMatchObject({ h: 28 });
  expect(await h(page.locator('.ds-sols'))).toBe(56);
  expect(await h(page.getByRole('button', { name: '+ 고르기' }))).toBe(34);
  await page.mouse.move(10, 890);
  await page.locator('#ds-add-space').blur();
  await shot(page, 'DS2');

  // DS2_AI — AI 업종 추론(점선 · 수락) · AI 공간 추천(점선 공간) · AI 공간별 제품 자동 매칭(점선 제품) · 점선 줄 「AI 추천 n개」
  await page.getByRole('button', { name: 'AI 업종 추론' }).click();
  await expect(page.getByRole('button', { name: '업종 오피스 · 업무시설' })).toHaveClass(/ds-ind__btn--pend/, { timeout: 20_000 });
  await expect(page.locator('.ds-ind .ds-by')).toHaveText('AI 추론');
  await expect(page.locator('.ds-ind__k')).toHaveText(`업종 · 근거 ${sb.ref} ‘입주사 공용 회의실 예약’ · ‘단지 운영’ — 복합단지일 수도 있어요`);
  await page.getByRole('button', { name: 'AI 공간 추천' }).click();
  await expect(page.locator('[data-rec]')).toHaveCount(5, { timeout: 20_000 });
  await expect(card(page, '전시 공간').locator('.ds-sp__basis')).toHaveText(`AI 추천 · ${sb.ref} 2 · 반도체 박물관 협업 전시`);
  await expect(card(page, '주차장').locator('.ds-sp__basis')).toHaveText('확장 공간 · 요구에는 없음');
  await page.getByRole('button', { name: 'AI 공간별 제품 자동 매칭' }).click();
  await expect(page.locator('[data-by="ai-pending"]').first()).toBeVisible({ timeout: 30_000 });
  const pendBar = page.locator('.cd-pendbar');
  await expect(pendBar).toContainText(/AI 추천 \d+개 — 점선은 수락해야 들어가요 · 하나씩 수락하거나 ×로 지워요/);
  const doc1 = await (await request.get(`/api/dss/v1/dss/${dssId}`)).json();
  await expect(pendBar).toContainText(`AI 추천 ${doc1.counts.pending}개`);
  // 보드 DS2_AI: 점선 줄 1100 × 38 · 점선 공간 카드 · 점선 제품 줄(수락 22 · × 20)
  expect(await box(pendBar)).toMatchObject({ w: 1100, h: 38 });
  expect(await box(card(page, '라운지'))).toMatchObject({ w: 266 });
  const pend0 = page.locator('[data-by="ai-pending"]').first();
  expect(await h(pend0.getByRole('button', { name: /^수락 · / }))).toBe(22);
  expect(await h(pend0.getByRole('button', { name: /^빼기 · / }))).toBe(20);
  await page.mouse.move(10, 890);
  await shot(page, 'DS2_AI');

  // 수락 · 지우기 — 업종 수락 · 추천 공간 하나 수락(점선 제품 그대로) · 하나 × · 나머지 모두 수락
  await page.locator('.ds-ind__ok').click();
  await expect(page.getByRole('button', { name: '업종 오피스 · 업무시설' })).toHaveClass(/ds-ind__btn--set/);
  await expect(page.locator('.ds-ind .ds-by')).toHaveText('AI 추론 · 수락');
  await card(page, '전시 공간').getByRole('button', { name: '수락 · 전시 공간 공간' }).click();
  await expect(card(page, '전시 공간')).not.toHaveAttribute('data-rec');
  await expect(card(page, '전시 공간').locator('.ds-sp__basis')).toHaveText(`근거 · ${sb.ref} 2 · 반도체 박물관 협업 전시`);
  await card(page, '주차장').getByRole('button', { name: '공간 빼기 · 주차장' }).click();
  await expect(card(page, '주차장')).toHaveCount(0);
  const firstPend = card(page, '로비').locator('[data-by="ai-pending"]').first();
  const firstName = (await firstPend.getAttribute('data-product'))!;
  await firstPend.getByRole('button', { name: `수락 · ${firstName}` }).click();
  await expect(prow(page, '로비', firstName)).toHaveAttribute('data-by', 'ai-accepted');
  await expect(prow(page, '로비', firstName).locator('.ds-by')).toHaveText('AI');
  await pendBar.getByRole('button', { name: '모두 수락' }).click();
  await expect(page.locator('[data-by="ai-pending"]')).toHaveCount(0);
  await expect(pendBar).toHaveCount(0);
  await expect(page.locator('[data-rec]')).toHaveCount(0);
  // 머리 「작성 중 · 공간 n · 제품 m …」은 다시 열 때(이번 방문은 새로 만들기)
  // 제품 탐색에서 고르기(ProdPicker 760×640) — 카드 안 찾기 칸 「제품 탐색」
  await card(page, '전시 공간').getByRole('button', { name: '전시 공간에 제품 추가' }).click();
  await card(page, '전시 공간').getByRole('button', { name: '제품 탐색' }).click();
  const picker = page.getByRole('dialog', { name: '전시 공간에 넣을 제품 고르기' });
  await expect(picker).toBeVisible();
  expect(await box(picker)).toMatchObject({ w: 760, h: 640 });
  await picker.locator('#wm-pick-search').fill('협업 전시 미디어월');
  await picker.getByRole('checkbox', { name: /협업 전시 미디어월.*직접 추가 · KB 에 없음 · 확인 필요/ }).last().click();
  await expect(picker.getByText(/\d+개 골랐어요/)).toBeVisible();
  await picker.getByRole('button', { name: '완료' }).click();
  await expect(prow(page, '전시 공간', '협업 전시 미디어월')).toBeVisible();
  await expect(prow(page, '전시 공간', '협업 전시 미디어월').locator('.ds-prow__model')).toHaveAttribute('title', '협업 전시 미디어월 · 직접 추가 · KB 에 없음 · 확인 필요');
  // 공간 이름 바로 고치기(떠날 때 저장)
  const nm = page.getByRole('textbox', { name: '공간 이름 · 공용 회의실' });
  await nm.fill('공용 회의실 A');
  await nm.press('Enter');
  await expect(card(page, '공용 회의실 A')).toBeVisible();

  // DS4 — 솔루션 「+ 고르기」 → 솔루션 고르기 팝업(820 × 700)
  await page.getByRole('button', { name: '+ 고르기' }).click();
  const sol = page.getByRole('dialog', { name: '솔루션 고르기' });
  await expect(sol).toBeVisible();
  expect(await box(sol)).toMatchObject({ w: 820, h: 700 });
  await expect(sol).toContainText('솔루션 고르기 · 0개 이상');
  await expect(sol).toContainText(`${name} 공간 제품과 함께 쓸 솔루션 · 고르지 않아도 저장돼요`);
  await expect(sol.locator('[data-solution="magicinfo"]')).toBeVisible({ timeout: 15_000 });
  await expect(sol.locator('.ds-solp__line')).toHaveText('솔루션 없이 닫아도 돼요');
  await expect(sol.locator('[data-solution="magicinfo"] .ds-solc__desc')).toContainText('함께 쓰는 제품');
  expect(await box(sol.locator('.ds-solp__head'))).toMatchObject({ w: 820, h: 72 });
  expect(await box(sol.locator('.ds-solp__foot'))).toMatchObject({ w: 820, h: 72 });
  expect(await box(sol.locator('[data-solution="magicinfo"]'))).toMatchObject({ w: 772 });
  expect(await h(sol.getByRole('button', { name: 'AI 솔루션 추천' }))).toBe(36);
  expect(await h(sol.getByRole('button', { name: '고른 솔루션 넣기' }))).toBe(44);
  expect(await h(sol.getByRole('button', { name: 'MagicINFO 상세' }))).toBe(32);
  await page.mouse.move(10, 890);
  await shot(page, 'DS4');
  // 겹침 안내(MagicINFO + VXT) → VXT 빼기
  await sol.locator('[data-solution="magicinfo"]').getByRole('checkbox').click();
  await sol.locator('[data-solution="vxt"]').getByRole('checkbox').click();
  const overlap = sol.locator('.ds-solp__overlap');
  await expect(overlap).toHaveText('MagicINFO와 Samsung VXT는 둘 다 사이니지 CMS예요. 같은 사이니지에 함께 쓰는 경우는 드물어요.');
  expect(await box(overlap)).toMatchObject({ w: 772, h: 36 });
  await expect(sol.locator('.ds-solp__line')).toHaveText('솔루션 2개 골랐어요 · 넣으면 DSS 화면의 솔루션 칸에 들어가요');
  await sol.locator('[data-solution="vxt"]').getByRole('checkbox').click();
  await expect(overlap).toHaveCount(0);
  // 취소하면 문서는 그대로
  await sol.getByRole('button', { name: '취소' }).click();
  await expect(sol).toHaveCount(0);
  await expect(page.locator('.ds-sols__t')).toHaveText('솔루션 0');

  // DS4_AI — 「AI 솔루션 추천」(띠) → 팝업이 열리며 바로 추천(mock: MagicINFO · SmartThings Pro · b.IoT 점선 · 근거)
  await page.locator('.ds-sols').getByRole('button', { name: 'AI 솔루션 추천' }).click();
  await expect(sol).toBeVisible();
  await expect(sol.locator('.ds-solc--rec')).toHaveCount(3, { timeout: 20_000 });
  const recIds = await sol.locator('.ds-solc--rec').evaluateAll((els) => els.map((e) => e.getAttribute('data-solution')));
  expect(recIds).toEqual(['magicinfo', 'smartthings_pro', 'biot']);
  await expect(sol.locator('[data-solution="magicinfo"] .ds-solc__why')).toHaveText(`근거 · ${sb.ref} 1 입주사 안내 · 사이니지`);
  await sol.locator('[data-solution="magicinfo"]').getByRole('checkbox').click();
  await expect(sol.locator('[data-solution="magicinfo"]')).toHaveClass(/ds-solc--on/);
  await expect(sol.locator('[data-solution="magicinfo"] .ds-solc__ai')).toHaveText('AI 추천');          // 보드 DS4_AI: 고른 뒤에도 AI 추천 · 근거
  await expect(sol.locator('[data-solution="magicinfo"] .ds-solc__why')).toBeVisible();
  await expect(sol.locator('.ds-solp__line')).toHaveText('솔루션 1개 골랐어요 · 넣으면 DSS 화면의 솔루션 칸에 들어가요');
  await page.mouse.move(10, 890);
  await shot(page, 'DS4_AI');
  // 상세 → 셸 솔루션 시트(팝업 위)
  await sol.getByRole('button', { name: 'SmartThings Pro 상세' }).click();
  await expect(page).toHaveURL(/detail=solution(%3A|:)smartthings_pro/);
  await expect(page.getByRole('dialog', { name: 'SmartThings Pro 솔루션 상세' })).toBeVisible();
  await page.keyboard.press('Escape');                       // 시트만 닫힌다 — 솔루션 고르기 팝업 · 고른 것은 그대로
  await expect(page).not.toHaveURL(/detail=/);
  await expect(sol).toBeVisible();
  await expect(sol.locator('[data-solution="magicinfo"]')).toHaveClass(/ds-solc--on/);
  await sol.locator('[data-solution="smartthings_pro"]').getByRole('checkbox').click();
  await sol.locator('[data-solution="biot"]').getByRole('checkbox').click();
  await sol.getByRole('button', { name: '고른 솔루션 넣기' }).click();
  await expect(sol).toHaveCount(0);
  // 솔루션 띠: 칩(최대 236 · 근거 · AI 추천 · ×)
  await expect(page.locator('.ds-sols__t')).toHaveText('솔루션 3');
  const chip = page.locator('.ds-chip[data-solution="magicinfo"]');
  await expect(chip.locator('.ds-chip__basis')).toHaveText('입주사 안내 · 사이니지');
  await expect(chip.locator('.ds-by')).toHaveText('AI 추천');
  for (const id of ['magicinfo', 'smartthings_pro', 'biot']) expect(await w(page.locator(`.ds-chip[data-solution="${id}"]`))).toBeLessThanOrEqual(236);
  expect(await h(chip)).toBe(34);

  const doc2 = await (await request.get(`/api/dss/v1/dss/${dssId}`)).json();
  const nProducts = doc2.counts.products as number;
  const nSpaces = doc2.counts.spaces as number;
  expect(doc2.counts).toMatchObject({ solutions: 3, pending: 0 });

  // 저장 → 같은 화면이 저장됨(DS_View): 참조 알약 · 「눌러서 바로 고쳐요」 · flow.json · 후속 작업 · 토스트
  await page.getByRole('button', { name: /^저장$/ }).click();
  await expect(head.locator('.cd-ref')).toHaveText(/^DSS-\d+ v1$/, { timeout: 20_000 });
  const code = (await head.locator('.cd-ref').textContent())!.replace(' v1', '');
  await expect(page.getByText(`${code} v1 저장 · ${sb.id} 요약본에 반영했어요`)).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/dss/${dssId}$`));
  await expect(head.locator('.cd-meta')).toHaveText(new RegExp(`^오늘 \\d\\d:\\d\\d 저장 · 공간 ${nSpaces} · 제품 ${nProducts} · 솔루션 3$`));
  await expect(head.getByText('눌러서 바로 고쳐요')).toBeVisible();
  await expect(page.getByRole('button', { name: /^저장/ })).toHaveCount(0);
  const nexts = page.locator('a.cd-nextcard');
  await expect(nexts).toHaveCount(2);
  await expect(nexts.nth(0)).toHaveAttribute('href', `/scenario/new?sb=${sb.id}&auto=1`);
  await expect(nexts.nth(0)).toContainText(`공간 시나리오 생성공간 ${nSpaces}개에서 사용자가 겪는 장면을 만들어요만들기`);
  await expect(nexts.nth(1)).toHaveAttribute('href', `/spec/new?sb=${sb.id}&auto=1`);
  await expect(nexts.nth(1)).toContainText(`매칭한 제품 ${nProducts}개를 스펙 시트로`);
  await expect(page.locator('.wm-sbbar__stage').first()).toHaveText('DSS까지');
  // 보드 DS_View: 후속 작업 2칸 544 × 76(간격 12) · 본문은 그 위를 채우고 안에서만 스크롤
  expect(await box(nexts.nth(0))).toMatchObject({ w: 544, h: 76, x: 300 });
  expect(await box(nexts.nth(1))).toMatchObject({ w: 544, h: 76, x: 856 });
  expect(await box(page.getByRole('button', { name: 'flow.json' }))).toMatchObject({ h: 38 });
  const doc3 = await (await request.get(`/api/dss/v1/dss/${dssId}`)).json();
  expect(doc3).toMatchObject({ status: 'done', ver: 1, changes: 0 });
  await page.mouse.move(10, 890);
  await expect(page.getByText(`${code} v1 저장 · ${sb.id} 요약본에 반영했어요`)).toHaveCount(0, { timeout: 6_000 });   // 토스트가 걷힌 뒤 캡처
  await shot(page, 'DS_View');

  // 허브 flow.json stages.dss — §6 계약 모양(점선 대기 값은 빠진다)
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const st = flow.stages.dss;
  expect(st.ref).toBe(code);
  expect(st.ver).toBe(1);
  expect(st.industry).toMatchObject({ value: '오피스 · 업무시설', by: 'ai-accepted' });
  expect(st.spaces.map((s: { name: string }) => s.name).slice(0, 3)).toEqual(['로비', '공용 회의실 A', '전시 공간']);
  expect(st.spaces[2]).toMatchObject({ by: 'ai-accepted', basis: `${sb.ref} 2 · 반도체 박물관 협업 전시` });
  expect(st.spaces[0].products[0]).toMatchObject({ name: 'Smart Signage QM55C', kind: 'product', ref: 'kb:model:mdl_LH55QMCEBGCXKR', qty: '2대', by: 'manual' });
  expect(st.spaces.flatMap((s: { products: Array<{ by: string }> }) => s.products).every((p: { by: string }) => p.by !== 'ai-pending')).toBe(true);
  expect(st.solutions.map((s: { name: string; by: string }) => [s.name, s.by])).toEqual([['MagicINFO', 'ai-accepted'], ['SmartThings Pro', 'ai-accepted'], ['b.IoT', 'ai-accepted']]);
  expect(st.counts).toEqual({ spaces: nSpaces, products: nProducts, solutions: 3 });
  expect(flow.cells.find((c: { key: string }) => c.key === 'dss')).toMatchObject({ state: 'done', ref: code, route: `/dss/${dssId}` });

  // DS_ViewJson — flow.json 팝업(이 콘텐츠 줄 강조)
  await page.getByRole('button', { name: 'flow.json' }).click();
  const dlg = page.getByRole('dialog', { name: new RegExp(`${sb.id}/flow\\.json`) });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByText('"dss": {').first()).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'DS_ViewJson');
  await page.keyboard.press('Escape');
  await expect(dlg).toHaveCount(0);

  // DS2_Edit — 수량 하나 고치기 → 「고친 곳 1」 · 그 칸 cd-in--chg · 「저장 · v2」 · 되돌리기
  await qty(page, 'Smart Signage QM55C').fill('3대');
  await qty(page, 'Smart Signage QM55C').press('Enter');
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 1');
  await expect(head.locator('.cd-ref')).toHaveText(`${code} v1 · 고치는 중`);
  await expect(head.locator('.cd-meta')).toHaveText(`${code} v1 고치는 중 · 저장하면 v2 · ${sb.id}에 반영돼요`);
  await expect(qty(page, 'Smart Signage QM55C')).toHaveClass(/cd-in--chg/);
  await expect(page.locator('.wm-sbbar__note')).toHaveText('저장하면 반영돼요');
  // 제품 하나 더(카드 안 찾기 · 직접) → 더한 줄 cd-chgrow · 고친 곳 2
  await card(page, '공용 회의실 A').getByRole('button', { name: '공용 회의실 A에 제품 추가' }).click();
  const find2 = page.getByRole('combobox', { name: '공용 회의실 A에 제품 추가' });
  await find2.fill('스마트 모니터');
  await page.getByRole('listbox', { name: '공용 회의실 A 제품 찾기 결과' }).getByRole('option', { name: '스마트 모니터 직접 추가 · KB 에 없음 · 확인 필요' }).click();
  await expect(prow(page, '공용 회의실 A', '스마트 모니터')).toHaveClass(/cd-chgrow/);
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 2');
  await page.keyboard.press('Escape');
  expect(await box(page.getByRole('button', { name: '저장 · v2' }))).toMatchObject({ h: 42 });
  expect(await h(page.getByRole('button', { name: '되돌리기' }))).toBe(38);
  await page.mouse.move(10, 890);
  await expect(page.locator('.wm-toast')).toHaveCount(0, { timeout: 6_000 });
  await shot(page, 'DS2_Edit');
  // 고친 채로 다른 화면으로 가면 묻는다(셸 ContentDetail) → 계속 고치기
  await page.getByRole('link', { name: '공간별 제품 매칭 DSS' }).first().click();
  const leave = page.getByRole('dialog', { name: '저장하지 않은 고친 곳' });
  await expect(leave).toContainText('고친 곳 2개를 아직 저장하지 않았어요');
  await leave.getByRole('button', { name: '계속 고치기' }).click();
  await expect(page).toHaveURL(new RegExp(`/dss/${dssId}$`));
  // 되돌리기 → 저장한 판(수량 2대 · 더한 제품 빠짐) · 「눌러서 바로 고쳐요」
  await page.getByRole('button', { name: '되돌리기' }).click();
  await expect(page.getByText(`${code} v1로 되돌렸어요`)).toBeVisible();
  await expect(head.locator('.cd-chg')).toHaveCount(0);
  await expect(head.getByText('눌러서 바로 고쳐요')).toBeVisible();
  await expect(qty(page, 'Smart Signage QM55C')).toHaveValue('2대');
  await expect(qty(page, 'Smart Signage QM55C')).not.toHaveClass(/cd-in--chg/);
  await expect(prow(page, '공용 회의실 A', '스마트 모니터')).toHaveCount(0);
  // 다시 고쳐 저장 → v2
  await qty(page, 'Smart Signage QM55C').fill('4대');
  await qty(page, 'Smart Signage QM55C').press('Enter');
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 1');
  await page.getByRole('button', { name: '저장 · v2' }).click();
  await expect(head.locator('.cd-ref')).toHaveText(`${code} v2`, { timeout: 20_000 });
  await expect(page.getByText(`${code} v2 저장 · ${sb.id} 요약본에 반영했어요`)).toBeVisible();
  await expect(qty(page, 'Smart Signage QM55C')).not.toHaveClass(/cd-in--chg/);
  const flow2 = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  expect(flow2.stages.dss.ver).toBe(2);
  expect(flow2.stages.dss.spaces[0].products[0].qty).toBe('4대');

  // 목록에 저장된 카드(DSS-nn v2) · 팝업은 「DSS-nn v2 있음」 · 예전 주소(?step=solution)도 상세
  await page.goto('/dss');
  const listRow = page.locator('.fl-card').filter({ hasText: name });
  await expect(listRow).toContainText(`${code} v2`);
  await expect(listRow.locator('.fl-cardtitle')).toHaveAttribute('href', `/dss/${dssId}`);
  await page.goto('/dss/new');
  await expect(page.getByRole('radio', { name: new RegExp(name) })).toContainText(`${code} v2 있음`);
  await page.goto(`/dss/${dssId}?step=solution`);
  await expect(page.locator('.cd-head .cd-ref')).toHaveText(`${code} v2`);
});

test('DSS — Storyboard 「만들기」(?sb=&auto=1)는 팝업을 건너뛰고 바로 상세 · 1920 폭 · 업종 목록 · 공간 빼기 · 저장 막힘', async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makePangyo(request, `판교 바로 만들기 ${tag()}`);
  await page.goto(`/dss/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/dss\/dss_[0-9A-Za-z]+$/, { timeout: 15_000 });
  await expect(page.locator('.cd-head .cd-ref')).toHaveText('새로 만들기');
  await expect(page.locator('.wm-sbbar__chip')).toContainText(sb.name);
  // 공간 · 제품 없이 저장하면 막힌다(셸 ContentDetail canSave — aria-disabled · 이유 title · 누르면 이유 토스트)
  const save = page.getByRole('button', { name: /^저장$/ });
  await expect(save).toHaveAttribute('aria-disabled', 'true');
  await expect(save).toHaveAttribute('title', '공간을 하나 이상 넣어 주세요');
  await save.click({ force: true });
  await expect(page.getByText('공간을 하나 이상 넣어 주세요').last()).toBeVisible();
  // 1920 × 1080: 본문 열은 1180 가운데 · 안쪽 1100 · 카드 4열 그대로
  await page.locator('#ds-add-space').fill('카페');
  await page.locator('#ds-add-space').press('Enter');
  await expect(card(page, '카페').locator('.ds-sp__basis')).toHaveText('직접 추가한 공간');
  await page.setViewportSize({ width: 1920, height: 1080 });
  expect(await w(page.locator('.wm-flow'))).toBe(1180);
  expect(await w(page.locator('.ds-body'))).toBe(1100);
  expect(await w(card(page, '카페'))).toBe(266);
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(save).toHaveAttribute('title', '공간에 제품을 하나 이상 넣어 주세요 · 수락하지 않은 추천은 저장되지 않아요');
  await save.click({ force: true });
  await expect(page.getByText('공간에 제품을 하나 이상 넣어 주세요 · 수락하지 않은 추천은 저장되지 않아요').last()).toBeVisible();
  // 업종 고르기(220 목록 · 8개 · 보드 순서)
  await page.getByRole('button', { name: '업종 선택해 주세요' }).click();
  const menu = page.getByRole('listbox', { name: '업종' });
  await expect(menu.getByRole('option')).toHaveText(['오피스 · 업무시설', '리테일', '외식 · 카페', '호텔 · 숙박', '병원 · 헬스케어', '교육', '공공 · 관공서', '주거 · 복합단지']);
  expect(await box(menu)).toMatchObject({ w: 220 });
  expect(await h(menu.getByRole('option').first())).toBe(34);
  await menu.getByRole('option', { name: '외식 · 카페' }).click();
  await expect(menu).toHaveCount(0);
  await expect(page.getByRole('button', { name: '업종 외식 · 카페' })).toHaveClass(/ds-ind__btn--set/);
  await expect(page.locator('.ds-ind .ds-by')).toHaveText('직접');
  // 공간 빼기(×)
  await card(page, '카페').getByRole('button', { name: '공간 빼기 · 카페' }).click();
  await expect(card(page, '카페')).toHaveCount(0);
  await expect(page.locator('.ds-fact').nth(0)).toHaveText('공간0');
  // 다시 열면 「작성 중」(무언가 썼다 · 업종)
  await page.reload();
  await expect(page.locator('.cd-head .cd-ref')).toHaveText('작성 중');
  await expect(page.locator('.cd-head .cd-meta')).toContainText('작성 중 · 공간 0 · 제품 0 · 솔루션 0 · ');
});
