/**
 * 여정 1 — 고객 요구사항(RQ) → 전략 Storyboard(SB) → 정의서 「쓰는 곳」 → 정의서 새 버전 → Storyboard 동기화 띠.
 * 실제 스택만(page.route 흉내 없음). RQ 는 화면에서 파일로 채워 저장하고, SB 는 RQ4 「다음」 카드로 들어간 뒤
 * 기획 방향 · 목차는 API 로 진행한다(그 화면들은 storyboard 기능 e2e 가 본다).
 */
import { expect, test } from '@playwright/test';
import { api, advanceStoryboard, backendDown, budget, fixture, getSb, ID, MEMO_TXT, open, RFP_PPTX, shot, until } from './helpers';

test.describe.configure({ mode: 'serial', timeout: 120_000 });

let rqId = '';
let sbId = '';

test.beforeAll(async ({ request }) => {
  const down = await backendDown(request, ['requirements', 'storyboard', 'mi', 'proposal']);
  test.skip(!!down, down ?? '');
});

test('RQ 파일로 채우기 → 바로 저장 v1 → RQ4 「전략 수립 Storyboard」 → SB1 정의서가 골라진 채', async ({ page }) => {
  budget(180_000);
  await open(page, '/requirements/legacy/new');
  await page.locator('[data-testid=rq-file-input]').setInputFiles([fixture('requirements', RFP_PPTX), fixture('requirements', MEMO_TXT)]);
  await expect(page).toHaveURL(/\/requirements\/rq_[0-9A-Z]{26}\/form$/, { timeout: 60_000 });
  rqId = page.url().match(ID('rq'))![0];
  // 채우기가 끝나면 첨부 버튼이 돌아오고 칸이 채워진다
  await expect(page.getByRole('button', { name: '파일 첨부' })).toBeVisible({ timeout: 120_000 });
  await expect(page.locator('#f-cust')).toHaveValue('E 자산운용', { timeout: 30_000 });
  await page.getByRole('button', { name: '바로 저장' }).click();
  await expect(page).toHaveURL(new RegExp(`/requirements/${rqId}/saved`), { timeout: 60_000 });
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('저장했어요');
  await expect(page.getByTestId('saved-version')).toHaveText('v1');
  await shot(page, 'J1-rq4-saved');

  // RQ4 다음 카드 → Storyboard(정의서 미리 선택)
  await page.locator('.rq-nextcard', { hasText: '전략 수립 Storyboard' }).click();
  await expect(page).toHaveURL(/\/storyboard\/sb_[0-9A-HJKMNP-TV-Z]{26}\/source$/, { timeout: 60_000 });
  sbId = page.url().match(ID('sb'))![0];
  const card = page.locator('.sb-choices .sb-choice[aria-pressed="true"]');
  await expect(card).toHaveCount(1, { timeout: 30_000 });
  await expect(card).toContainText('E 자산운용');
  await expect(card.locator('.sb-ver')).toHaveText('v1');
  await shot(page, 'J1-sb1-source');
  const sb = await getSb(page.request, sbId);
  expect(sb.requirement_ref?.requirement_id).toBe(rqId);
});

test('SB 목차 · 저장 → RQ6 「쓰는 곳」 Storyboard 칩이 그 Storyboard 로 · SB4 다음 카드 3', async ({ page, request }) => {
  budget(240_000);
  test.skip(!sbId, '앞 단계 실패');
  await advanceStoryboard(request, sbId, 'saved');
  // 정의서 사용 링크(요구사항 쪽에 등록됐는지)
  const links = await api(request, 'requirements', 'GET', `/requirements/${rqId}/links`);
  const mine = links.items.find((l: any) => l.service === 'storyboard' && l.ref_id === sbId);
  expect(mine, 'storyboard 링크 등록').toBeTruthy();
  expect(mine.sync_state).toBe('up_to_date');

  await open(page, `/requirements/${rqId}`);
  await expect(page.getByTestId('doc-version')).toHaveText('정의서 v1');
  const use = page.locator('.rq-usechip', { hasText: 'Storyboard' });
  await expect(use).toBeVisible();
  await shot(page, 'J1-rq6-usage');
  await use.click();
  await expect(page).toHaveURL(new RegExp(`/storyboard/${sbId}(/|$)`), { timeout: 30_000 });

  // SB4 저장 완료 — 다음에 할 일(제안서 · MI · 공간 시나리오)
  await open(page, `/storyboard/${sbId}/saved`);
  await expect(page.getByTestId('handoff-proposal')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('handoff-mi')).toBeVisible();
  await expect(page.getByTestId('handoff-scenario')).toBeVisible();
  await shot(page, 'J1-sb4-handoffs');
});

test('SB4 「Market Intelligence」 → MI1 이 정의서 · Storyboard 를 가져온 새 분석 · RQ6 쓰는 곳 MI', async ({ page, request }) => {
  budget(120_000);
  test.skip(!sbId, '앞 단계 실패');
  await open(page, `/storyboard/${sbId}/saved`);
  await page.getByTestId('handoff-mi').click();
  await expect(page).toHaveURL(/\/mi\/mi_[0-9A-HJKMNP-TV-Z]{26}\/input$/, { timeout: 60_000 });
  const miId = page.url().match(ID('mi'))![0];
  const a = await api(request, 'mi', 'GET', `/analyses/${miId}`);
  expect(a.links.requirements_id).toBe(rqId);
  expect(a.links.storyboard_id).toBe(sbId);
  expect(a.customer_name).toBe('E 자산운용');
  await shot(page, 'J1-mi1-from-sb');
  const links = await api(request, 'requirements', 'GET', `/requirements/${rqId}/links`);
  expect(links.items.some((l: any) => l.service === 'mi' && l.ref_id === miId), 'mi 링크 등록').toBeTruthy();
  // 정의서 쓰는 곳 MI 칩 → 이 분석
  await open(page, `/requirements/${rqId}`);
  await page.locator('.rq-usechip', { hasText: 'MI' }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/${miId}`), { timeout: 30_000 });
  await request.delete(`/api/mi/v1/analyses/${miId}`).catch(() => null);
});

test('SB4 「공간 시나리오」 → SC 가 Storyboard 공간 · 고객을 미리 채운 새 시나리오', async ({ page, request }) => {
  budget(90_000);
  test.skip(!sbId, '앞 단계 실패');
  await open(page, `/storyboard/${sbId}/saved`);
  await page.getByTestId('handoff-scenario').click();
  await expect(page).toHaveURL(new RegExp(`/scenario/legacy/new\\?sb=${sbId}`), { timeout: 30_000 });   // /scenario/new 는 새 흐름(Gate) — 이전 Storyboard 넘기기는 legacy
  await shot(page, 'J1-sc1-from-sb');
  await page.getByTestId('sc1-next').click();
  await expect(page).toHaveURL(/\/scenario\/sc_[0-9A-HJKMNP-TV-Z]{26}\/input$/, { timeout: 30_000 });
  const scId = page.url().match(ID('sc'))![0];
  const sc = await api(request, 'scenario', 'GET', `/scenarios/${scId}`);
  // Storyboard Part 2 공간 · 고객을 미리 채운다(09-scenario 상태 갱신)
  expect(sc.customer_name).toBe('E 자산운용');
  expect(sc.raw_text ?? '').toContain('[공간]');
  const sb = await getSb(request, sbId);
  expect(sc.project_id ?? null, '시나리오가 Storyboard 프로젝트를 잇는다').toBe(sb.project_id ?? null);
  await request.delete(`/api/scenario/v1/scenarios/${scId}`).catch(() => null);
});

test('정의서 v2 저장 → Storyboard 목차 위 「요구사항 정의서 v2가 새로 저장됐어요 · 저장 메모」 → 반영하기 → 링크 v2', async ({ page, request }) => {
  budget(240_000);
  test.skip(!sbId, '앞 단계 실패');
  const cur = await api(request, 'requirements', 'GET', `/requirements/${rqId}`);
  const item = cur.form.keymen[0].items[0];
  await api(request, 'requirements', 'PATCH', `/requirements/${rqId}/draft`, { ops: [{ op: 'update_item', item_id: item.id, text: `${item.text} — 입주사 앱 연동` }] });
  const s = await api(request, 'requirements', 'POST', `/requirements/${rqId}/save`, { note: '통합 시험 v2' });
  expect(s.version).toBe(2);
  // Storyboard 는 20초에 한 번 정의서를 확인한다
  await until(() => getSb(request, sbId), (x: any) => x.rq_update?.version === 2, 60_000, 'Storyboard rq_update');
  await open(page, `/storyboard/${sbId}/outline`);
  const band = page.getByTestId('rq-update-band');
  await expect(band).toContainText('요구사항 정의서 v2', { timeout: 30_000 });
  await expect(band).toContainText('통합 시험 v2');     // 띠 한 줄 = 변경 수 · 저장 메모(rq_update.note)
  await shot(page, 'J1-sb3-rq-update');
  await band.getByRole('button', { name: '반영하기' }).click();
  await expect(page).toHaveURL(new RegExp(`/storyboard/${sbId}/versions`), { timeout: 30_000 });
  await until(() => getSb(request, sbId), (x: any) => !x.active_job && x.requirement_ref?.version === 2, 120_000, 'Storyboard 동기화');
  const links = await until(() => api(request, 'requirements', 'GET', `/requirements/${rqId}/links`),
    (l: any) => l.items.some((x: any) => x.service === 'storyboard' && x.ref_id === sbId && x.rq_version === 2), 60_000, '링크 v2');
  expect(links.items.find((x: any) => x.service === 'storyboard').sync_state).toBe('up_to_date');
});
