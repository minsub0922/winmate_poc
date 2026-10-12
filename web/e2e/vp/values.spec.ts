/**
 * VP 상세 한 장(웹앱 ① v63 — 보드 webapp1 View content=vp + VPBody · VP1 · VP2 · VP_Draft · VP2_AI · VP2_Pick · VP2_Edit · VP_View · VP2_Detail).
 * Storyboard(rq → dss, API) → 목록 → 「새 VP 만들기」→ 목록 위 팝업에서 Storyboard 고르기 → 상세(새로 만들기 · DSS 제품 · 솔루션 가져옴 · 가치 없음)
 * → 그 자리에서 가치 · 니즈 쓰기 · AI 니즈 추론 · AI 가치 매칭 추천(점선 → 수락) · 제품 · 솔루션 고르기(ProdPicker) → 저장 → 저장됨(완료 화면 없음)
 * → 한 칸 고치기 → 「고친 곳 1」 → 되돌리기 → 두 칸 고치기(VP2_Edit) → 저장 · v2 → 연결된 가치 전체(VpDetail).
 * 보드 고정 칸(줄 그리드 200 | 1fr · 본문 1100 · 띠 48 · 줄 38 · 팝업 760×640 · 900×720)을 숫자로 재고 `__screens__/<보드>.png` 를 남긴다.
 * 실행: make e2e-feature SERVICE=vp (또는 cd web && WM_E2E_SUITE=vp WM_E2E_DEV=1 WM_E2E_PORT=5205 npx playwright test e2e/vp/values.spec.ts --workers=1)
 */
import { test, type Locator, type Page } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { expect, shot } from './helpers';

const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
const w = async (l: Locator) => (await box(l)).w;
const h = async (l: Locator) => (await box(l)).h;
const row = (page: Page, name: string) => page.getByRole('group', { name, exact: true });
/** 그 줄의 n번째 가치 칸 */
const val = (page: Page, name: string, i: number) => row(page, name).locator('.vb-val').nth(i);
/** 캡처 전: 마우스를 치우고 토스트가 사라질 때까지 */
const rest = async (page: Page) => { await page.mouse.move(10, 890); await expect(page.locator('.wm-toast')).toHaveCount(0, { timeout: 8_000 }); };

test('VP 상세 한 장 — 팝업에서 Storyboard → 바로 입력 · AI 점선 수락 · 고르기 → 저장 → 고친 곳 · 되돌리기 → v2 · 연결된 가치', async ({ page, request }) => {
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `용산 AI Ready 오피스 ${tag()}`;
  const sb = await makeStoryboard(request, { dss: true, name });
  const hub = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const dssRef = hub.stages.dss.ref as string;
  const rqRef = hub.stages.rq.ref as string;

  // VP0 → 「새 VP 만들기」 → 목록 위 팝업(보드 VP1 = Gate)
  await page.goto('/vp');
  await expect(page.getByRole('heading', { name: 'Value Proposition', exact: true })).toBeVisible();
  await page.getByRole('link', { name: /새 VP 만들기/ }).click();
  await expect(page).toHaveURL(/\/vp\/new$/);
  const gate = page.getByRole('dialog', { name: '새 VP 만들기 · Storyboard 고르기' });
  await expect(gate.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  const radio = gate.getByRole('radio', { name: new RegExp(name) });
  await radio.click();
  await expect(radio).toHaveAttribute('aria-checked', 'true');
  await page.mouse.move(10, 890);
  await shot(page, 'VP1');
  await gate.getByRole('button', { name: /이 Storyboard로 시작/ }).click();

  // VP2 — 새로 만들기(DSS 제품 6 · 솔루션 2 를 가져왔고 가치는 없음) · 단계 · 완료 화면 없음
  await expect(page).toHaveURL(/\/vp\/values\/vmap_[0-9A-Za-z]+$/, { timeout: 30_000 });
  const mapId = page.url().split('/').pop()!;
  const head = page.locator('.cd-head');
  await expect(head.locator('.cd-h1')).toHaveText(name);
  await expect(head.locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(head.locator('.cd-meta')).toHaveText(`새로 만드는 중 · 쓰는 대로 작성 중으로 남아요 · 저장하면 ${sb.id}에 연결돼요`);
  await expect(page.getByText('저장하면 이 Storyboard에 연결돼요 · 사전 작업에서 골랐어요')).toBeVisible();
  await expect(page.locator('.vb-from')).toHaveText(`${dssRef}에서 8개를 골랐어요`);
  await expect(page.locator('.vb-out')).toHaveText('· 고르지 않은 것 없음');
  await expect(page.getByRole('button', { name: '제품 · 솔루션 고르기 · 8' })).toBeVisible();
  await expect(page.locator('.vb-row .vb-name')).toHaveText(['The Wall IAB 146"', 'Smart Signage QM55C', '삼성 키오스크', 'Flip Pro WA75D', 'Smart Signage QB55C', '옥외형 사이니지 OHC55', 'MagicINFO', 'SmartThings Pro']);
  const wall = row(page, 'The Wall IAB 146"');
  await expect(wall.locator('.vb-where')).toHaveText('로비');
  await expect(wall.locator('.vb-count')).toHaveText('가치 없음');
  await expect(wall.locator('.vb-count')).toHaveCSS('color', 'rgb(122, 79, 0)');
  await expect(row(page, 'MagicINFO').locator('.wm-kindtag')).toHaveText('솔루션');
  await expect(wall.locator('.vb-add')).toHaveText('+ 가치 추가 · 공간 · 가치 · 니즈 · 요구 — 또는 위의 AI 가치 매칭 추천');
  await expect(page.locator('.cd-pendbar')).toHaveCount(0);
  // 보드 VPBody: 본문 열 1180 → 본문 1100 · 띠 48 · 줄 그리드 200 | 1fr(gap 16 · 좌우 18 → 1100 − 2 − 36 − 216 = 846) · 버튼 36 · 더하기 34 · 저장 42
  expect(await w(page.locator('.wm-flow'))).toBe(1180);
  expect(await w(page.locator('.cd-body'))).toBe(1100);
  expect(await h(page.locator('.vb-strip'))).toBe(48);
  expect(await w(wall.locator('.vb-left'))).toBe(200);
  expect(await w(wall.locator('.vb-right'))).toBe(846);
  expect(await h(page.getByRole('button', { name: '제품 · 솔루션 고르기 · 8' }))).toBe(36);
  expect(await h(page.getByRole('button', { name: 'AI 가치 매칭 추천', exact: true }))).toBe(36);
  expect(await h(wall.locator('.vb-add'))).toBe(34);
  expect(await h(head.getByRole('button', { name: '저장', exact: true }))).toBe(42);
  expect((await box(page.locator('.vb-panel'))).y + (await h(page.locator('.vb-panel')))).toBe(900 - 22);   // 높이를 채운다(아래 22)
  await rest(page);
  await shot(page, 'VP2');

  // 바로 입력 — The Wall: 가치 + 니즈(직접) + 연결 요구(Storyboard 요구사항에서 고르기)
  await wall.locator('.vb-add').click();
  const v0 = val(page, 'The Wall IAB 146"', 0);
  await expect(v0.getByLabel('가치 메시지')).toBeFocused();
  await v0.getByLabel('가치 메시지').fill('들어서는 순간 회사의 AI 비전을 보여 줌');
  await v0.getByLabel('가치 메시지').press('Enter');
  await expect(wall.locator('.vb-count')).toHaveText('가치 1 · 니즈 0/1');
  await expect(head.locator('.cd-ref')).toHaveText('작성 중');
  await v0.getByLabel('고객의 니즈').fill('방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요');
  await v0.getByLabel('고객의 니즈').press('Enter');
  await expect(v0.locator('.cd-tag')).toHaveText('직접');
  await v0.getByRole('button', { name: '연결 요구 · 없음' }).click();
  const reqList = page.getByRole('listbox', { name: '연결 요구' });
  await reqList.getByRole('option', { name: `${rqRef} 최초 AI Ready 오피스` }).click();
  await expect(v0.getByRole('button', { name: `연결 요구 · ${rqRef} 최초 AI Ready 오피스` })).toBeVisible();
  await expect(wall.locator('.vb-count')).toHaveText('가치 1 · 니즈 1/1');
  // 둘째 가치(니즈 비움 → 주황 점선 칸 + AI 니즈 추론)
  await wall.getByRole('button', { name: '+ 가치 추가', exact: true }).click();
  const v1 = val(page, 'The Wall IAB 146"', 1);
  await v1.getByLabel('가치 메시지').fill('사내 행사 때 로비를 무대로 바꿈');
  await v1.getByLabel('가치 메시지').press('Enter');
  await expect(wall.locator('.vb-count')).toHaveText('가치 2 · 니즈 1/2');
  await expect(v1.getByLabel('고객의 니즈')).toHaveClass(/vb-need--empty/);
  await expect(v1.getByLabel('고객의 니즈')).toHaveAttribute('placeholder', '고객이 할 말처럼 적어요 · 예) 여름에도 쾌적한 교실 환경이 필요해요');
  expect(await w(v0.getByRole('button', { name: /^공간/ })) > 30).toBe(true);
  expect(await h(v0.getByLabel('가치 메시지'))).toBe(32);
  expect(await h(v1.getByRole('button', { name: 'AI 니즈 추론' }))).toBe(28);
  // Flip Pro — 니즈 없는 가치 하나(저장 뒤 VP2_Edit 에서 채운다)
  const flip = row(page, 'Flip Pro WA75D');
  await flip.locator('.vb-add').click();
  await val(page, 'Flip Pro WA75D', 0).getByLabel('가치 메시지').fill('케이블 없이 바로 화면 공유');
  await val(page, 'Flip Pro WA75D', 0).getByLabel('가치 메시지').press('Enter');
  await expect(flip.locator('.vb-count')).toHaveText('가치 1 · 니즈 0/1');
  await expect(head.locator('.cd-meta')).toContainText('작성 중 · 가치 3 · 니즈 1/3 · ');
  await page.locator('.vb-panel').evaluate((el) => { el.scrollTop = 0; });
  await rest(page);
  await shot(page, 'VP_Draft');

  // AI 니즈 추론(mock: '행사' → 고정 문장) → 점선 칸 · 수락(VP2_AI 에서 그대로 둔다)
  await v1.getByRole('button', { name: 'AI 니즈 추론' }).click();
  await expect(v1.getByLabel('고객의 니즈')).toHaveValue('행사 때마다 외부 장소를 빌리지 않았으면 해요', { timeout: 30_000 });
  await expect(v1.getByLabel('고객의 니즈')).toHaveClass(/vb-need--pend/);
  await expect(v1.getByRole('button', { name: '수락' })).toBeVisible();
  await expect(page.locator('.cd-pendbar')).toContainText('AI 추천 1개');

  // AI 가치 매칭 추천(mock vp.values_suggest.v1 — 보드 VP2_AI 의 후보) → 점선 가치 칸 + 일괄 줄
  await page.getByRole('button', { name: 'AI 가치 매칭 추천', exact: true }).click();
  const pend = page.locator('.cd-pendbar');
  await expect(pend).toHaveText(/AI 추천 5개 — 가치 후보와 빈 니즈 추론이 점선으로 들어왔어요 · 수락해야 들어가요/, { timeout: 30_000 });
  expect(await box(pend)).toMatchObject({ x: 300, w: 1100, h: 38 });
  const v2 = val(page, 'The Wall IAB 146"', 2);
  await expect(v2).toHaveClass(/vb-val--pend/);
  await expect(v2.getByLabel('가치 메시지')).toHaveValue('베젤 없는 큰 화면으로 콘텐츠에 몰입');
  await expect(v2.getByLabel('고객의 니즈')).toHaveValue('로비 화면이 광고판처럼 보이지 않았으면 해요');
  await expect(wall.locator('.vb-count')).toHaveText('가치 2 · 니즈 1/2');
  await expect(row(page, 'Smart Signage QM55C').locator('.vb-val--pend')).toHaveCount(2);
  await expect(row(page, 'Smart Signage QM55C').locator('.vb-count')).toHaveText('가치 없음');
  await expect(head.locator('.cd-meta')).toContainText('작성 중 · 가치 3 · 니즈 1/3');
  await page.locator('.vb-panel').evaluate((el) => { el.scrollTop = 0; });
  await rest(page);
  await shot(page, 'VP2_AI');
  // 하나씩 수락(니즈 · 가치) → 나머지 모두 수락
  await v1.getByRole('button', { name: '수락' }).click();
  await expect(v1.locator('.cd-tag')).toHaveText('AI 추론 · 수락');
  await v2.getByRole('button', { name: '수락' }).click();
  await expect(v2).not.toHaveClass(/vb-val--pend/);
  await expect(wall.locator('.vb-count')).toHaveText('가치 3 · 니즈 3/3');
  await expect(pend).toContainText('AI 추천 3개');
  await pend.getByRole('button', { name: '모두 수락' }).click();
  await expect(page.locator('.cd-pendbar')).toHaveCount(0);
  await expect(row(page, 'Smart Signage QM55C').locator('.vb-count')).toHaveText('가치 2 · 니즈 2/2');

  // 제품 · 솔루션 고르기(ProdPicker 760×640) — QB55C · OHC55 빼기
  await page.getByRole('button', { name: '제품 · 솔루션 고르기 · 8' }).click();
  const pick = page.getByRole('dialog', { name: 'VP에 넣을 제품 · 솔루션 고르기' });
  await expect(pick.getByText(`${dssRef} · 제품`, { exact: true })).toBeVisible();
  await expect(pick.getByRole('checkbox', { name: /The Wall IAB 146"/ })).toContainText(`${dssRef} · 로비`);
  await pick.getByRole('checkbox', { name: /Smart Signage QB55C/ }).click();
  await pick.getByRole('checkbox', { name: /옥외형 사이니지 OHC55/ }).click();
  await expect(pick.getByText('6개 골랐어요')).toBeVisible();
  expect(await box(pick)).toMatchObject({ w: 760, h: 640 });
  await rest(page);
  await shot(page, 'VP2_Pick');
  await pick.getByRole('button', { name: '완료' }).click();
  await expect(page.locator('.vb-from')).toHaveText(`${dssRef}에서 6개를 골랐어요`);
  await expect(page.locator('.vb-out')).toHaveText('· 고르지 않은 2 — Smart Signage QB55C · 옥외형 사이니지 OHC55');
  await expect(page.locator('.vb-row')).toHaveCount(6);

  // 저장 → 그 자리에서 저장됨(보드 VP_View) · 완료 화면 없음
  await head.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: new RegExp(`VP-\\d+ v1 저장 · ${sb.id}에 반영했어요`) })).toBeVisible({ timeout: 30_000 });
  await expect(head.locator('.cd-ref')).toHaveText(/^VP-\d+ v1$/);
  const code = (await head.locator('.cd-ref').textContent())!.replace(' v1', '');
  await expect(head.locator('.cd-meta')).toHaveText(/^오늘 \d\d:\d\d 저장 · 제품 · 솔루션 6 · 가치 7 · 고객의 니즈 6\/7$/);
  await expect(head.getByText('눌러서 바로 고쳐요')).toBeVisible();
  await expect(head.getByRole('button', { name: /flow\.json/ })).toBeVisible();
  await expect(head.getByRole('button', { name: '저장', exact: true })).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/vp/values/${mapId}$`));
  const flow1 = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  expect(flow1.stages.vp).toMatchObject({ ref: code, ver: 1, selection: { fromDss: 6, excluded: ['Smart Signage QB55C', '옥외형 사이니지 OHC55'] } });
  expect(flow1.stages.vp.counts).toMatchObject({ items: 6, values: 7, needs: 6 });
  await page.locator('.vb-panel').evaluate((el) => { el.scrollTop = 0; });
  await rest(page);
  await shot(page, 'VP_View');

  // 한 칸 고치기 → 「고친 곳 1」 · 그 칸은 cd-in--chg · 저장 · v2 → 되돌리기
  await v1.getByLabel('가치 메시지').fill('사내 행사 · 투자자 설명회 때 로비를 무대로 바꿈');
  await v1.getByLabel('가치 메시지').press('Enter');
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 1');
  await expect(head.locator('.cd-ref')).toHaveText(`${code} v1 · 고치는 중`);
  await expect(head.locator('.cd-meta')).toHaveText(`${code} v1 고치는 중 · 저장하면 v2 · ${sb.id}에 반영돼요`);
  await expect(v1.getByLabel('가치 메시지')).toHaveClass(/cd-in--chg/);
  await expect(head.getByRole('button', { name: '저장 · v2' })).toBeVisible();
  await head.getByRole('button', { name: '되돌리기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: `${code} v1로 되돌렸어요` })).toBeVisible();
  await expect(head.locator('.cd-ref')).toHaveText(`${code} v1`);
  await expect(v1.getByLabel('가치 메시지')).toHaveValue('사내 행사 때 로비를 무대로 바꿈');
  await expect(v1.getByLabel('가치 메시지')).not.toHaveClass(/cd-in--chg/);
  expect((await (await request.get(`/api/vp/v1/value-maps/${mapId}`)).json()).changes).toBe(0);

  // 두 칸 고치기(보드 VP2_Edit: 가치 메시지 · 빈 니즈) → 고친 곳 2 → 저장 · v2
  await v1.getByLabel('가치 메시지').fill('사내 행사 · 투자자 설명회 때 로비를 무대로 바꿈');
  await v1.getByLabel('가치 메시지').press('Enter');
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 1');
  const fv = val(page, 'Flip Pro WA75D', 0);
  await fv.getByLabel('고객의 니즈').fill('회의 시작할 때 케이블 찾느라 시간 버리고 싶지 않아요');
  await fv.getByLabel('고객의 니즈').press('Enter');
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 2');
  await expect(fv.getByLabel('고객의 니즈')).toHaveClass(/cd-in--chg/);
  await expect(page.locator('.cd-in--chg')).toHaveCount(2);
  await page.locator('.vb-panel').evaluate((el) => { el.scrollTop = 0; });
  await rest(page);
  await shot(page, 'VP2_Edit');
  await head.getByRole('button', { name: '저장 · v2' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: `${code} v2 저장` })).toBeVisible({ timeout: 30_000 });
  await expect(head.locator('.cd-ref')).toHaveText(`${code} v2`);
  await expect(page.locator('.cd-in--chg')).toHaveCount(0);
  await expect(head.locator('.cd-meta')).toHaveText(/저장 · 제품 · 솔루션 6 · 가치 7 · 고객의 니즈 7\/7$/);
  const flow2 = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  expect(flow2.stages.vp.ver).toBe(2);

  // 연결된 가치 전체 보기(VpDetail 900×720)
  await wall.getByRole('button', { name: '연결된 가치 전체 보기 →' }).click();
  const det = page.getByRole('dialog', { name: /The Wall IAB 146".*연결된 가치/ });
  await expect(det).toContainText(`이 제안 · ${code}`);
  await expect(det).toContainText('들어서는 순간 회사의 AI 비전을 보여 줌');
  await expect(det).toContainText('고객의 니즈 · “방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요”');
  expect(await box(det)).toMatchObject({ w: 900, h: 720 });
  await rest(page);
  await shot(page, 'VP2_Detail');
  await det.getByRole('button', { name: '닫기' }).last().click();
  await expect(det).toHaveCount(0);

  // 목록 — 저장한 것은 「완성」 카드
  await page.goto('/vp');
  await expect(page.locator('.fl-card').filter({ hasText: name })).toContainText('완성');
});
