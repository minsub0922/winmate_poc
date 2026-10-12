/**
 * 공간 시나리오 새 흐름(웹앱 ① 보드 SC0 · SC1 · SC2 · SC2_AI · SC2_Pick · SC2_Empty · View content=sc(SC_View)) — Storyboard 허브 연동.
 * API 로 Storyboard(요구사항 + DSS)를 만들고 목록 → Gate → SC2(DSS 공간 미리 채움 · AI 3안 · 수락 · 직접 시나리오 · 제품 고르기 · 제품 없는 공간 막기)
 * → 저장 → 같은 주소의 보기(SC_View · 완료 안내 없음 · flow.json) → 허브 stages.sc 확인 → 편집(?edit=1) · 목록 「열기」 · 새로고침도 보기.
 * 보드 고정 칸(SC2 196 · 236 · View 236 | 1fr · 시나리오 카드 두 칸)과 본문 열(1180)을 숫자로 잰다.
 * 실제 스택(mock 모델 — 로비 AI 3안은 mocks/ai-tools/sc.space_candidates.v1.json 고정 응답).
 */
import { expect, test, type Page } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { shot } from './helpers';

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const width = async (page: Page, sel: string) => Math.round((await page.locator(sel).first().boundingBox())!.width);
const height = async (page: Page, sel: string) => Math.round((await page.locator(sel).first().boundingBox())!.height);

/** SC_View(보드 View content=sc) — 저장한 값 그대로 · 보드 폭(본문 1100 = 236 | 14 | 850 · 시나리오 카드 두 칸 같은 폭) */
async function expectView(page: Page, o: { title: string; sbName: string; dssRef: string }) {
  await expect(page.getByRole('heading', { name: o.title, level: 1 })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.fl-view__ref')).toHaveText(/^SC-\d+ v1$/);
  await expect(page.locator('.fl-view__meta')).toHaveText(/^오늘 \d\d:\d\d 저장 · 공간 3 · 시나리오 2 · 시나리오 없는 공간 2$/);
  await expect(page.locator('.wm-sbbar__chip')).toContainText(o.sbName);
  await expect(page.locator('.scv-spaces__h')).toHaveText(`공간 · ${o.dssRef}`);
  const sp = page.locator('.scv-sp');
  await expect(sp).toHaveText([/로비시나리오 2 · 제품 4/, /회의실시나리오 없음 · 제품 \d+/, /주차장시나리오 없음 · 제품 1/]);
  await expect(sp.first()).toHaveAttribute('aria-pressed', 'true');                   // 처음엔 시나리오가 있는 첫 공간
  await expect(page.locator('.scv-head__name')).toHaveText('로비');
  await expect(page.locator('.scv-head__n')).toHaveText('시나리오 2');
  await expect(page.locator('.scv-chip')).toHaveText(['제품The Wall IAB 146"', '제품Smart Signage QM55C', '제품삼성 키오스크', '솔루션MagicINFO']);
  const cards = page.locator('.scv-card');
  await expect(cards).toHaveCount(2);
  const a = cards.nth(0);
  await expect(a.locator('.scv-card__title')).toHaveText('미등록 방문객 응대');
  await expect(a.locator('.fl-vtag')).toHaveText('AI A안 · 수락');
  await expect(a.locator('.fl-vtag')).toHaveClass(/fl-vtag--ai/);
  await expect(a.locator('.scv-kv').first()).toHaveText('사용자예약 없이 온 외부 방문객');
  const b = cards.nth(1);
  await expect(b.locator('.scv-card__title')).toHaveText('출근 혼잡 시간의 로비');
  await expect(b.locator('.fl-vtag')).toHaveText('직접');
  await expect(b.locator('.scv-kv').first()).toHaveText('사용자오전 9시 전후 임직원');
  await expect(b.locator('.scv-pill')).toHaveText(['Smart Signage QM55C', 'MagicINFO']);
  await expect(b.locator('.scv-step')).toHaveText(['1출근 인원이 몰려 게이트 앞이 혼잡해짐', '2층별 엘리베이터 대기 안내가 뜸Smart Signage QM55C']);
  await expect(b.locator('.scv-step').nth(1).locator('.scv-sprod')).toHaveText('Smart Signage QM55C');
  await expect(b.locator('.scv-kv').last()).toHaveText('시간대오전 9시 전후');
  // 후속 작업 없음(보드 View content=sc) · 편집 링크 = ?edit=1
  await expect(page.locator('.fl-view__follow')).toHaveCount(0);
  await expect(page.getByRole('link', { name: '편집' })).toHaveAttribute('href', /\?edit=1$/);
  expect(await width(page, '.fl-view__body')).toBe(1100);
  expect(await width(page, '.scv-spaces')).toBe(236);
  expect(await width(page, '.scv-main')).toBe(850);
  expect(await height(page, '.scv-sp')).toBe(52);
  expect(await height(page, '.fl-view__ic')).toBe(44);
  const [w1, w2] = [Math.round((await cards.nth(0).boundingBox())!.width), Math.round((await cards.nth(1).boundingBox())!.width)];
  expect(w1).toBe(w2);
  expect(w1).toBeGreaterThanOrEqual(390);                                           // (850 − 2 − 32 − 12) / 2 = 402(세로 스크롤 막대가 생기면 그만큼 준다)
}

test('SC 새 흐름 — 목록 → Gate → 공간 · 시나리오 → 저장 → 보기 · 허브 stages.sc', async ({ page, request }) => {
  test.setTimeout(240_000);
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });
  const flow0 = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const dssRef: string = flow0.stages.dss.ref;
  await page.setViewportSize({ width: 1440, height: 900 });

  // ── SC0 목록(보드 List content=sc) ──
  await page.goto('/scenario');
  await expect(page.getByRole('heading', { name: '공간 시나리오 생성', level: 1 })).toBeVisible();
  await expect(page.getByText('Storyboard의 공간마다 사용자 시나리오를 만들어요.')).toBeVisible();
  await expect(page.getByText('사전 작업 · 최소 DSS까지 된 Storyboard')).toBeVisible();
  await shot(page, 'SC0-new');
  await page.locator('.fl-hero').click();
  await expect(page).toHaveURL(/\/scenario\/new$/);

  // ── SC1 Gate — 스텝바 「Storyboard · 공간별 시나리오」(보드 Gate META) ──
  await expect(page.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  await expect(page.getByText('공간별 시나리오', { exact: true })).toBeVisible();
  const row = page.getByRole('radio', { name: new RegExp(esc(sb.name)) });
  await row.click();
  await expect(row).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByText(`${sb.name}에 공간 시나리오가 연결돼요`)).toBeVisible();
  await page.mouse.move(0, 0);
  await shot(page, 'SC1-new');
  await page.getByRole('button', { name: /이 Storyboard로 시작/ }).click();
  await expect(page).toHaveURL(/\/scenario\/spaces\/scs_[^/]+$/, { timeout: 20_000 });
  const setId = page.url().split('/').pop()!;

  // ── SC2 — DSS 공간 · 공간별 제품 미리 채움 ──
  await expect(page.getByRole('heading', { name: '공간마다 시나리오를 여러 개 써요' })).toBeVisible();
  await expect(page.getByText('공간 · 시나리오', { exact: true })).toBeVisible();               // 보드 SC2 스텝바
  await expect(page.locator('.ss-spaces__h')).toHaveText(`공간 · ${dssRef}`);
  await expect(page.getByRole('tab')).toHaveText([/로비/, /회의실/, /주차장/]);
  await expect(page.getByRole('tab', { name: /로비/ })).toContainText('시나리오 0 · 제품 4');   // DSS 제품 3 + MagicINFO(links → 로비)
  await expect(page.locator('.ss-pchip')).toHaveText([/제품The Wall IAB 146"/, /제품Smart Signage QM55C/, /제품삼성 키오스크/, /솔루션MagicINFO/]);
  await expect(page.locator('.wm-sbbar__chip')).toContainText(sb.name);                        // 연결된 Storyboard 바 = 실제 허브
  await expect(page.getByRole('link', { name: 'Storyboard', exact: true })).toHaveAttribute('href', `/storyboard/flow/${sb.id}`);
  // 보드 폭: 본문 열 1180 · 패딩 32 → 공간 196 | 12 | (시나리오 236 | 10 | 편집 662) · 본문 높이 900-64-56-52 = 728
  expect(await width(page, '.wm-flow')).toBe(1180);
  expect(await width(page, '.ss-spaces')).toBe(196);
  expect(await width(page, '.ss-sphead')).toBe(908);
  expect(await width(page, '.ss-lpanel')).toBe(236);
  expect(await width(page, '.ss-ed')).toBe(662);
  expect(await height(page, '.wm-flow__section')).toBe(728);
  expect(await height(page, '.ss-sp')).toBe(52);
  expect(await height(page, '.wm-flow__primary')).toBe(48);

  // SC2_Empty — 시나리오 없는 공간(주차장)
  await page.getByRole('tab', { name: /주차장/ }).click();
  await expect(page.getByText('주차장 시나리오를 시작해요')).toBeVisible();
  await expect(page.getByText('아직 시나리오가 없어요. 직접 추가하거나 AI 3안을 받아 보세요.')).toBeVisible();
  await shot(page, 'SC2_Empty-new');

  // 제품 · 솔루션을 모두 빼면 주황 경고 · 저장 막힘 → 고르기로 다시 넣기
  await page.getByRole('button', { name: '옥외형 사이니지 OHC55 빼기' }).click();
  await expect(page.getByText('공간마다 제품 · 솔루션이 하나 이상 있어야 해요')).toBeVisible();
  await expect(page.getByRole('tab', { name: /주차장/ })).toContainText('제품 · 솔루션 없음');
  await expect(page.locator('.wm-flow__summary')).toHaveText('공간 3 · 시나리오 0 · 제품 · 솔루션 없는 공간 1');
  await expect(page.getByRole('button', { name: '저장', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: /AI 시나리오 3안/ })).toBeDisabled();
  await shot(page, 'SC2_NoProduct-new');
  await page.getByRole('button', { name: '+ 추가 · 변경' }).click();
  let dlg = page.getByRole('dialog', { name: '주차장 · 제품 · 솔루션 고르기' });
  await expect(dlg.getByText(`${dssRef} · 제품`, { exact: true })).toBeVisible();
  await dlg.getByRole('checkbox', { name: /옥외형 사이니지 OHC55/ }).click();
  await expect(dlg.getByText('1개 골랐어요')).toBeVisible();
  await dlg.getByRole('button', { name: '완료' }).click();
  await expect(page.getByRole('button', { name: '저장', exact: true })).toBeEnabled();

  // SC2_Pick — 로비 고르기(DSS 제품 · 솔루션 묶음, 있던 공간 표시)
  await page.getByRole('tab', { name: /로비/ }).click();
  await page.getByRole('button', { name: '+ 추가 · 변경' }).click();
  dlg = page.getByRole('dialog', { name: '로비 · 제품 · 솔루션 고르기' });
  await expect(dlg.getByText(`${dssRef} · 솔루션`, { exact: true })).toBeVisible();
  await expect(dlg.getByRole('checkbox', { name: /SmartThings Pro/ })).toHaveAttribute('aria-checked', 'false');
  await expect(dlg.getByRole('checkbox', { name: /Flip Pro WA75D/ })).toContainText(`${dssRef} · 회의실`);
  await expect(dlg.getByText('4개 골랐어요')).toBeVisible();
  expect(Math.round((await dlg.boundingBox())!.width)).toBe(760);
  await shot(page, 'SC2_Pick-new');
  await dlg.getByRole('button', { name: '완료' }).click();

  // SC2_AI — 로비 AI 3안(점선 A/B/C · 수락 전에도 고칠 수 있음)
  await page.getByRole('button', { name: /AI 시나리오 3안/ }).click();
  await expect(page.locator('.ss-sc--cand')).toHaveCount(3, { timeout: 30_000 });
  await expect(page.getByText('점선은 AI 후보')).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'AI 후보 A안이에요 · 수락해야 시나리오로 들어가요' })).toBeVisible();
  await expect(page.locator('#ss-title')).toHaveValue('미등록 방문객 응대');
  await expect(page.locator('.ss-ed')).toHaveClass(/wm-flow__panel--dashed/);
  await page.mouse.move(0, 0);
  await shot(page, 'SC2_AI-new');
  await page.locator('#ss-who').fill('예약 없이 온 외부 방문객');                 // 수락 전 편집
  await page.waitForTimeout(900);
  await page.getByRole('status').getByRole('button', { name: '수락' }).click();
  await expect(page.locator('.ss-sc--cand')).toHaveCount(2);
  await expect(page.getByRole('tab', { name: /로비/ })).toContainText('시나리오 1 · 제품 4');
  // B · C 빼기
  for (const t of ['사내 행사 날 로비', '퇴근 후 보안 모드']) {
    await page.locator('.ss-sc', { hasText: t }).click();
    await page.getByRole('status').getByRole('button', { name: '빼기' }).click();
    await expect(page.locator('.ss-sc', { hasText: t })).toHaveCount(0);
  }

  // 직접 시나리오(단계 · 쓰인 제품 · 자유 항목)
  await page.getByRole('button', { name: '+ 시나리오 추가' }).click();
  await page.locator('#ss-title').fill('출근 혼잡 시간의 로비');
  await page.locator('#ss-who').fill('오전 9시 전후 임직원');
  await page.getByRole('checkbox', { name: 'The Wall IAB 146"' }).click();      // 이 시나리오에서 빼기
  await page.getByRole('checkbox', { name: '삼성 키오스크' }).click();
  await page.locator('#ss-step-0').fill('출근 인원이 몰려 게이트 앞이 혼잡해짐');
  await page.getByRole('button', { name: '+ 단계 추가' }).click();
  await page.locator('#ss-step-1').fill('층별 엘리베이터 대기 안내가 뜸');
  await page.locator('.ss-ptag').nth(1).click();                                  // 쓰인 제품 → 첫 시나리오 제품
  await expect(page.locator('.ss-ptag').nth(1)).toHaveText('Smart Signage QM55C');
  await page.getByRole('button', { name: '+ 시간대' }).click();
  await page.locator('#ss-f-0').fill('오전 9시 전후');
  await expect(page.locator('.ss-sc', { hasText: '출근 혼잡 시간의 로비' })).toContainText('제품 2 · 단계 2');
  await page.waitForTimeout(1200);                                                // 자동 저장(600ms)
  await page.locator('.ss-sc', { hasText: '미등록 방문객 응대' }).click();
  await expect(page.locator('.ss-sc', { hasText: '미등록 방문객 응대' })).toContainText('AI A안 · 수락');
  await expect(page.locator('#ss-who')).toHaveValue('예약 없이 온 외부 방문객');
  await expect(page.locator('.wm-flow__summary')).toHaveText('공간 3 · 시나리오 2');
  await page.mouse.move(0, 0);
  await shot(page, 'SC2-new');

  // ── 저장 → SC_View(보드 View content=sc) — 같은 주소의 그 공간 시나리오 보기(「저장했어요」 같은 완료 안내는 없다) ──
  await page.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.locator('.scv-grid')).toBeVisible({ timeout: 20_000 });
  await expect(page).toHaveURL(new RegExp(`/scenario/spaces/${setId}$`));
  await expect(page.getByText(/저장했어요|완료됐|완성됐|다시 고치기|전체 JSON 보기/)).toHaveCount(0);
  await expectView(page, { title: sb.name, sbName: sb.name, dssRef });
  // 다른 공간을 누르면 오른쪽이 그 공간으로(시나리오 없는 공간 = 점선 안내)
  await page.getByRole('button', { name: /회의실/ }).click();
  await expect(page.getByRole('button', { name: /회의실/ })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.scv-head__name')).toHaveText('회의실');
  await expect(page.locator('.scv-head__n')).toHaveText('시나리오 0');
  await expect(page.locator('.scv-empty')).toContainText('이 공간은 시나리오가 없어요');
  await expect(page.locator('.scv-card')).toHaveCount(0);
  await page.getByRole('button', { name: /로비/ }).click();
  await expect(page.locator('.scv-card')).toHaveCount(2);
  await page.mouse.move(10, 890);
  await shot(page, 'SC_View-new');
  await page.getByRole('button', { name: 'flow.json' }).click();
  const json = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(json).toBeVisible();
  await expect(json.getByText('"sc": {').first()).toBeVisible();
  await expect(json.getByText('이 콘텐츠가 담긴 줄')).toBeVisible();
  await shot(page, 'SC_ViewJson-new');
  await json.getByRole('button', { name: '닫기' }).last().click();

  // 허브 flow.json stages.sc · 진행 칸 · 팝업 카드
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const sc = flow.stages.sc;
  const set = await (await request.get(`/api/scenario/v1/space-sets/${setId}`)).json();
  expect(sc.ref).toBe(set.code);
  expect(sc.ver).toBe(1);
  expect(sc.from).toBe(dssRef);
  expect(sc.spaces.map((s: { name: string }) => s.name)).toEqual(['로비', '회의실', '주차장']);
  const lobby = sc.spaces[0];
  expect(lobby.scenarios.map((x: { title: string; by: string }) => [x.title, x.by])).toEqual([['미등록 방문객 응대', 'ai-candidate-A'], ['출근 혼잡 시간의 로비', 'manual']]);
  expect(lobby.scenarios[0].user).toBe('예약 없이 온 외부 방문객');
  expect(lobby.scenarios[1].products).toEqual(['Smart Signage QM55C', 'MagicINFO']);
  expect(lobby.scenarios[1].steps[1]).toEqual({ text: '층별 엘리베이터 대기 안내가 뜸', product: 'Smart Signage QM55C' });
  expect(lobby.scenarios[1].fields).toEqual([{ k: '시간대', v: '오전 9시 전후' }]);
  expect(sc.counts).toEqual({ spaces: 3, scenarios: 2, spacesWithoutScenario: 2 });
  const cell = flow.cells.find((c: { key: string }) => c.key === 'sc');
  expect(cell.state).toBe('done');
  expect(cell.route).toBe(`/scenario/spaces/${setId}`);
  expect(flow.cards.sc.facts).toEqual([['공간', '3'], ['시나리오', '2'], ['시나리오 없는 공간', '2']]);

  // 편집 → ?edit=1 편집 화면(같은 묶음 · 머리 = 코드)
  await page.getByRole('link', { name: '편집' }).click();
  await expect(page).toHaveURL(new RegExp(`/scenario/spaces/${setId}\\?edit=1$`));
  await expect(page.getByRole('heading', { name: '공간마다 시나리오를 여러 개 써요' })).toBeVisible();
  await expect(page.locator('.ss-sc', { hasText: '출근 혼잡 시간의 로비' })).toBeVisible();
  await expect(page.locator('.scv-grid')).toHaveCount(0);

  // 목록 — 저장된 공간 시나리오 줄 · 연결된 Storyboard 칩 · 「열기」 → 보기 · 새로고침해도 보기
  await page.goto('/scenario');
  const listRow = page.locator('.fl-card', { hasText: `${set.code} v1` });
  await expect(listRow).toContainText(sb.name);
  await expect(listRow.locator('.fl-cardtitle')).toHaveAttribute('href', `/scenario/spaces/${setId}`);
  await shot(page, 'SC0-list-new');
  await listRow.locator('.fl-cardtitle').click();
  await expect(page).toHaveURL(new RegExp(`/scenario/spaces/${setId}$`));
  await expectView(page, { title: sb.name, sbName: sb.name, dssRef });
  await page.reload();
  await expectView(page, { title: sb.name, sbName: sb.name, dssRef });

  // Gate — 이미 SC 가 있는 Storyboard 는 수정 / 복제본
  await page.goto(`/scenario/new?sb=${sb.id}`);
  await expect(page.getByText(`이 Storyboard에는 공간 시나리오 ${set.code} v1이 이미 있어요`)).toBeVisible();
  await expect(page.getByRole('button', { name: `${set.code} 수정하기` })).toBeVisible();

  // 편집 화면에서 다시 저장 → ?edit 를 떼고 보기로(완료 안내 · 토스트 없음) · v2
  await page.goto(`/scenario/spaces/${setId}?edit=1`);
  await expect(page.getByRole('heading', { name: '공간마다 시나리오를 여러 개 써요' })).toBeVisible();
  await page.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/scenario/spaces/${setId}$`), { timeout: 20_000 });
  await expect(page.locator('.fl-view__ref')).toHaveText(`${set.code} v2`);
  await expect(page.locator('.scv-card')).toHaveCount(2);
  await expect(page.getByText(/저장했어요|완료됐|완성됐/)).toHaveCount(0);
});

test('SC 새 흐름 — Storyboard 화면의 「만들기」(?sb=&auto=1)는 Gate 를 건너뛴다 · 옛 주소는 이전 흐름으로', async ({ page, request }) => {
  test.setTimeout(120_000);
  const sb = await makeStoryboard(request, { dss: true, name: `판교 스타트업 단지 ${tag()}` });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/scenario/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/scenario\/spaces\/scs_[^/]+$/, { timeout: 20_000 });
  await expect(page.getByRole('tab', { name: /로비/ })).toBeVisible();
  await expect(page.locator('.wm-sbbar__chip')).toContainText(sb.name);

  // DSS 전 Storyboard 는 Gate 에서 고를 수 없다(「DSS 먼저」)
  const pre = await makeStoryboard(request, { name: `동탄 시니어 복합단지 ${tag()}` });
  await page.goto(`/scenario/new?sb=${pre.id}&auto=1`);
  await expect(page.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  const off = page.getByRole('radio', { name: new RegExp(esc(pre.name)) });
  await expect(off).toHaveAttribute('aria-disabled', 'true');
  await expect(off).toContainText('DSS 먼저');
  const r = await request.post('/api/scenario/v1/space-sets', { data: { sb_id: pre.id } });
  expect(r.status()).toBe(422);
  expect((await r.json()).error.code).toBe('PREREQUISITE_MISSING');

  // 이전 흐름은 /scenario/legacy 아래 · 다른 기능 · 서버 handoff 가 만드는 옛 주소는 주소 그대로 이전 화면
  await page.goto('/scenario/legacy');
  await expect(page.getByTestId('sc0-new')).toHaveAttribute('href', '/scenario/legacy/new');
  await page.getByTestId('sc0-new').click();
  await expect(page).toHaveURL(/\/scenario\/legacy\/new$/);
  await expect(page.getByTestId('sc1-with')).toBeVisible();
  await page.goto('/scenario/new?sb=sb_01HZZZZZZZZZZZZZZZZZZZZZZZ');               // 이전 Storyboard SB4 handoff
  await expect(page.getByTestId('sc1-with')).toBeVisible();
  await page.goto('/scenario/new?from=vp:vp_x');                                // VP4 재료
  await expect(page.getByTestId('sc1-with')).toBeVisible();
  await expect(page).toHaveURL(/\/scenario\/new\?from=vp:vp_x$/);
  await page.goto('/scenario/new/template');                                     // UC_SC · 다른 기능 링크
  await expect(page.getByTestId('sc1t-tile')).toHaveCount(16);
  await page.goto('/scenario/legacy/new/template');
  await expect(page.getByTestId('sc1t-tile')).toHaveCount(16);
  await page.goto('/scenario/spaces/new');
  await expect(page).toHaveURL(/\/scenario\/new$/);
  await expect(page.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
});
