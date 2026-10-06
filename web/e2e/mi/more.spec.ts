/**
 * 실제 mi · 플랫폼 · mock 모델 위의 나머지 흐름:
 * AC-MI-84(MI1I 프리셋 → MI2) · 85(MI2C 가중치 비율) · 53 · 54 · 55(MI3R 변경 안 · 되돌리기 · 적용) · 65(연결 제안서로 바로 넘김).
 */
import { expect, test } from '@playwright/test';
import { MI_ID, api, backendDown, seedDesigned, seedDone, shot } from './helpers';

test.describe.configure({ mode: 'serial' });

test('MI1I → MI2 — 업종 프리셋으로 요구 4개 · 기준 4개 · 업종 고정 (AC-MI-84)', async ({ page, request }) => {
  test.setTimeout(120_000);
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');

  await page.goto('/mi/new/industry?segment=FB');
  const tiles = page.getByRole('radiogroup', { name: '업종' });
  await expect(tiles.getByRole('radio', { checked: true })).toContainText('외식 · 카페');
  const reqs = page.getByRole('checkbox');
  await expect(reqs.first()).toBeVisible();
  const n = await reqs.count();
  expect(n).toBeGreaterThanOrEqual(4);
  for (let i = 0; i < n; i += 1) await expect(reqs.nth(i)).toHaveAttribute('aria-checked', i < 4 ? 'true' : 'false');
  const labels = await Promise.all([0, 1, 2, 3].map((i) => reqs.nth(i).locator('.mi-req__label').innerText()));
  await expect(page.getByText('고객 요구사항 ← 요구 4개')).toBeVisible();
  await expect(page.getByText('경쟁 비교 기준 ← 같은 4개')).toBeVisible();
  await expect(page.locator('.mi-apply__chip').nth(2)).toContainText('MI-FB-A · B · C');
  await shot(page, 'mi1i-preset');

  await page.getByTestId('mi1i-apply').click();
  await expect(page).toHaveURL(new RegExp(`/mi/${MI_ID.source}/scope$`));
  const id = page.url().match(MI_ID)![0];
  const a = await api(request, 'GET', `/analyses/${id}`);
  expect(a.segment.code).toBe('FB');
  expect(a.segment.mode).toBe('pin');
  const preset = a.requirements.filter((r: any) => r.origin === 'preset');
  expect(preset.map((r: any) => r.text)).toEqual(labels);
  const crit = await api(request, 'GET', `/analyses/${id}/criteria`);
  const pc = crit.items.filter((c: any) => c.source === 'preset');
  expect(pc).toHaveLength(4);
  expect(pc.map((c: any) => c.name)).toEqual(labels.map((l) => l.slice(0, 24)));
  for (const c of pc) expect(c.source_label).toMatch(/^업종 사례 \d+건$/);

  // MI2 — 범위 4개 · 실행 버튼(약 3분)
  await expect(page.getByText('분석할 범위를 골라주세요.', { exact: false })).toBeVisible();
  const boxes = page.locator('.mi-scope__card input[type="checkbox"]');
  await expect(boxes).toHaveCount(4);
  for (let i = 0; i < 4; i += 1) await expect(boxes.nth(i)).toBeChecked();
  await expect(page.getByTestId('mi-dock-title')).toHaveText('분석 범위 · 복수 선택 · 4개 선택됨 · 2 / 3');
  await expect(page.getByTestId('mi2-run')).toHaveText('분석 시작 (약 3분)');
  // 업종은 고정이라 묻지 않고, 설계의 나머지를 조용히 채운 뒤 실행할 수 있다(§4.6)
  await expect(page.getByTestId('mi2-run')).toBeEnabled({ timeout: 60_000 });
  await expect(page).toHaveURL(new RegExp(`/mi/${id}/scope$`));
  const d = await api(request, 'GET', `/analyses/${id}/design`);
  expect(d.status).toBe('done');
  expect((await api(request, 'GET', `/analyses/${id}`)).segment).toMatchObject({ code: 'FB', mode: 'pin' });
  await shot(page, 'mi2-scope');
});

test('MI2C — 가중치 [5, 4, 3, 2, 1] → 33% · 27% · 20% · 13% · 7% (AC-MI-85)', async ({ page, request }) => {
  test.setTimeout(120_000);
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
  const a = await seedDesigned(request);
  const names = ['본사 원격 통합 관리', '전력 효율', '콘텐츠 운영 편의', '설치 · 유지보수', '가격'];
  await api(request, 'PUT', `/analyses/${a.id}/criteria`, { items: names.map((name, i) => ({ name, weight: 3, order: i, source: 'user' })) });

  await page.goto(`/mi/${a.id}/competitors`);
  await expect(page.getByTestId('mi2c-crit')).toHaveCount(5);
  await expect(page.getByTestId('mi2c-pct')).toHaveText(['20%', '20%', '20%', '20%', '20%']);
  for (const [i, w] of [5, 4, 3, 2, 1].entries()) {
    if (w !== 3) await page.getByRole('button', { name: `${names[i]} 가중치 ${w}`, exact: true }).click();
  }
  await expect(page.getByTestId('mi2c-pct')).toHaveText(['33%', '27%', '20%', '13%', '7%']);
  await expect(page.getByRole('group', { name: `${names[0]} 가중치 5 / 5` })).toBeVisible();
  await expect.poll(async () => (await api(request, 'GET', `/analyses/${a.id}/criteria`)).items.map((c: any) => c.weight), { timeout: 5_000 })
    .toEqual([5, 4, 3, 2, 1]);
  const crit = await api(request, 'GET', `/analyses/${a.id}/criteria`);
  expect(crit.items.map((c: any) => c.pct)).toEqual([33, 27, 20, 13, 7]);
  await expect(page.getByTestId('mi2c-comp').first()).toBeVisible();
  await shot(page, 'mi2c-competitors');
});

test('MI3R 행 추가 · 되돌리기 · 적용 → MI3 `제안서 MI 섹션으로` 바로 넘김 (AC-MI-53 · 54 · 55 · 65)', async ({ page, request }) => {
  test.setTimeout(240_000);
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
  const pid = 'prp_01M4E2EMIPROPOSAL00000001';
  const a = await seedDone(request, undefined, { links: { proposal_id: pid, proposal_title: 'A 커피 디지털 메뉴보드 제안', proposal_type: 'standard' } });
  expect(a.usage.value).toBe('standard');

  // MI3R — 경쟁사 탭만 다시 분석: `유지보수 · AS` 행 추가 1건
  await page.goto(`/mi/${a.id}/revise?scope=area&area=competitor`);
  await expect(page.getByRole('radiogroup', { name: '다시 분석할 범위' }).getByRole('radio', { checked: true })).toHaveText('경쟁사 탭');
  await page.getByLabel('수정 요청').fill('유지보수 · AS 행 추가해줘');
  await page.getByRole('button', { name: '보내기' }).click();
  await expect(page).toHaveURL(/[?&]rev=rev_/);
  const summary = page.getByTestId('mi3r-summary');
  await expect(summary).toContainText('바뀐 곳 1', { timeout: 60_000 });
  await expect(summary).toContainText('행 추가 1');
  const apply = page.getByTestId('mi3r-apply');
  await expect(apply).toHaveText('변경 1건 적용');
  await expect(apply).toBeEnabled();
  const added = page.locator('.mi-cmp__rowhead--added').filter({ hasText: '유지보수 · AS' });
  await expect(added).toContainText('추가');
  await expect(page.locator('[data-changed="row_add"]').first()).toBeVisible();
  await expect(page.getByTestId('mi3r-footer')).toContainText('출처 ');
  await shot(page, 'mi3r-revise');

  // 빼기 → 적용할 변경 없음(AC-MI-55) · 되돌린 변경에서 다시 적용(AC-MI-54)
  await added.getByRole('button', { name: '빼기' }).click();
  await expect(apply).toHaveText('변경 0건 적용');
  await expect(apply).toBeDisabled();
  await expect(apply).toHaveAttribute('title', '적용할 변경이 없어요');
  await expect(summary.getByRole('button', { name: '전부 되돌리기' })).toBeDisabled();
  await page.getByTestId('mi3r-reverted').getByRole('button', { name: '행 추가 다시 적용' }).click();
  await expect(apply).toHaveText('변경 1건 적용');
  await apply.click();
  await expect(page).toHaveURL(new RegExp(`/mi/${a.id}/result\\?tab=competitor`));
  await expect(page.getByRole('table', { name: '경쟁사 비교표' })).toContainText('유지보수 · AS');
  const after = await api(request, 'GET', `/analyses/${a.id}`);
  expect(after.version).toBe(2);

  // MI3 → 연결된 제안서로 바로(MI4 를 거치지 않음) · 넘김 기록 delivered(AC-MI-65)
  let imported: any = null;
  await page.route('**/api/proposal/v1/proposals/*/imports', async (route) => {
    imported = { url: route.request().url(), body: route.request().postDataJSON() };
    await route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ import_id: 'imp_e2e', job_id: null }) });
  });
  const patched = page.waitForResponse((r) => /\/api\/mi\/v1\/analyses\/[^/]+\/handoffs\/hof_/.test(r.url()) && r.request().method() === 'PATCH');
  await page.getByTestId('mi3-send').click();
  const hof = await (await patched).json();
  expect(hof.status).toBe('delivered');
  expect(hof.target_id).toBe(pid);
  await expect(page).toHaveURL(new RegExp(`/proposal/${pid}/sections/mi$`));
  expect(imported.url).toContain(`/proposals/${pid}/imports`);
  expect(imported.body.section_key).toBe('mi');
  expect(imported.body.source).toMatchObject({ feature: 'MI', ref_id: a.id, handoff_id: hof.id });
  expect(imported.body.include_keys.length).toBeGreaterThanOrEqual(3);
});

test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: 'ignoreErrors' }); });
