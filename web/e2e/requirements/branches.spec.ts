/**
 * 고객 요구사항(RQ) 갈래 화면 — docs/scenarios/01-requirements.md §9.2 E2E 1 · 3 · 4 · 5 · 14 · 15 · 16.
 * 기본 흐름(E2E 2 · 6 ~ 13)은 flow.spec.ts. 데이터는 테스트마다 새로 만든다(같은 dev 사용자를 여러 세션이 함께 쓴다).
 */
import { expect, test, type Page } from '@playwright/test';
import {
  MEMO, PPTX, RQ_ID, apiJson, attach, createRq, dragFiles, fakeId, fillWith, files, internalToken, shot, sum, uniq, waitSession, weightsOf,
  type Rq, type Session,
} from './helpers';

const crumb = (page: Page) => page.locator('.sh-crumbs__cur');

test('E2E 1 목록: 탭 수 · 이어서 · 열기 · 새 요구사항', async ({ page, request }) => {
  const U = uniq();
  const cust = `목록고객${U}`;
  const saved = await createRq(request, [
    { op: 'set_field', field: 'customer_name', value: cust }, { op: 'set_field', field: 'project_name', value: '저장한 건' },
  ]);
  await apiJson(request, 'POST', `/requirements/${saved.id}/save`, {});
  const open = await createRq(request, [
    { op: 'set_field', field: 'customer_name', value: cust }, { op: 'set_field', field: 'project_name', value: '쓰는 중인 건' },
  ]);

  await page.goto(`/requirements/legacy?q=${encodeURIComponent(cust)}`);
  const tabs = page.getByRole('tablist', { name: '상태' });
  await expect(tabs.getByRole('tab', { name: /^전체\s*2$/ })).toHaveAttribute('aria-selected', 'true');
  await expect(tabs.getByRole('tab', { name: /^진행 중\s*1$/ })).toBeVisible();
  await expect(tabs.getByRole('tab', { name: /^저장됨\s*1$/ })).toBeVisible();
  const table = page.getByRole('table', { name: '요구사항 목록' });
  const rowOpen = table.getByRole('row').filter({ hasText: '쓰는 중인 건' });
  const rowSaved = table.getByRole('row').filter({ hasText: '저장한 건' });
  await expect(rowOpen.getByRole('link', { name: '이어서' })).toBeVisible();
  await expect(rowOpen.locator('.rq-pill')).toHaveText('입력 중');
  await expect(rowSaved.getByRole('link', { name: '열기' })).toBeVisible();
  await expect(rowSaved.locator('.rq-pill')).toHaveText('저장됨 · v1');
  // 첫 행이 가장 최근
  await expect(table.getByRole('row').nth(1)).toContainText('쓰는 중인 건');
  await shot(page, 'rq0-list');

  await tabs.getByRole('tab', { name: /^저장됨/ }).click();
  await expect(page).toHaveURL(/tab=saved/);
  await expect(table.getByRole('row').filter({ hasText: cust })).toHaveCount(1);
  await rowSaved.getByRole('link', { name: '열기' }).click();
  await expect(page).toHaveURL(new RegExp(`/requirements/${saved.id}$`));
  await expect(page.getByTestId('doc-version')).toHaveText('정의서 v1');

  await page.goto(`/requirements/legacy?q=${encodeURIComponent(cust)}`);
  await rowOpen.getByRole('link', { name: '이어서' }).click();
  await expect(page).toHaveURL(new RegExp(`/requirements/${open.id}/form$`));
  await expect(page.locator('#f-proj')).toHaveValue('쓰는 중인 건');

  await page.goto('/requirements/legacy');
  await page.getByRole('link', { name: '새 요구사항' }).first().click();
  await expect(page).toHaveURL(/\/requirements\/legacy\/new$/);
  await expect(page.getByPlaceholder('예) 용산 업무시설 재개발 제안')).toBeVisible();
  await expect(page.getByPlaceholder('키맨 (예: 대표이사)')).toBeVisible();
  await expect(crumb(page)).toHaveText('새 요구사항');
  await expect(page.locator('[data-step="1"] [data-state="active"]')).toBeVisible();
});

test('E2E 2 · 3 · 5 끌어다 놓기 · 사람 값 보호', async ({ page, request }) => {
  test.setTimeout(120_000);
  const U = uniq();
  const mine = `직접 입력한 이름 ${U}`;
  await page.goto('/requirements/legacy/new');
  await page.getByPlaceholder('예) 용산 업무시설 재개발 제안').fill(mine);
  await expect(page).toHaveURL(/\/requirements\/rq_[0-9A-Z]{26}\/form$/);
  const id = page.url().match(RQ_ID)![0];
  await expect.poll(async () => (await apiJson<Rq>(request, 'GET', `/requirements/${id}`)).form.project_name.value).toBe(mine);
  await page.reload();
  await expect(page.locator('#f-proj')).toHaveValue(mine);

  // RQ1D 오버레이
  await dragFiles(page, [PPTX, MEMO], false);
  const overlay = page.getByRole('region', { name: '여기에 놓기' });
  await expect(overlay).toBeVisible();
  await expect(overlay).toContainText('놓으면 폼을 채워요');
  await expect(overlay).toContainText('파일 2개');
  await expect(overlay.locator('.rq-overlay__chip')).toHaveCount(2);
  await shot(page, 'rq1d-drag');
  await page.keyboard.press('Escape');
  await expect(overlay).toHaveCount(0);

  // 놓기 → RQ1G → RQ2
  await dragFiles(page, [PPTX, MEMO], true);
  await expect(page.locator('.rq-filechip')).toHaveCount(2);
  await expect(page.getByTestId('fill-progress')).toContainText('채우는 중');
  await expect(page.getByTestId('fill-progress')).toContainText(/\d+ \/ \d+/);
  await expect(page.getByRole('button', { name: '심층 작성' })).toHaveAttribute('aria-disabled', 'true');
  await expect(page.getByRole('button', { name: '파일 첨부' })).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('.rq-filechip[data-state="done"]')).toHaveCount(2);
  // 사람이 쓴 값은 그대로 · 배지 없음(E2E 5)
  await expect(page.locator('#f-proj')).toHaveValue(mine);
  await expect(page.locator('.rq-fld__box:has(#f-proj) .rq-src')).toHaveCount(0);
  await expect(page.locator('#f-cust')).toHaveValue('E 자산운용');
  await expect(page.locator('.rq-fld__box:has(#f-cust) .rq-src')).toHaveText('PPTX');
  await expect(page.locator('.rq-fld__box:has(#f-note) .rq-src')).toHaveText('TXT');
  await expect(page.getByTestId('equal-badge')).toHaveText('균등');
  const rq = await apiJson<Rq>(request, 'GET', `/requirements/${id}`);
  expect(rq.form.project_name.value).toBe(mine);
});

test('E2E 16 새로고침 복구: 채우는 중 새로고침 → 칩 · 진행 → RQ2', async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.goto('/requirements/legacy/new');
  const posted = page.waitForResponse((r) => r.request().method() === 'POST' && /\/requirements\/rq_[0-9A-Z]{26}\/files$/.test(r.url()));
  await attach(page, '[data-testid=rq-file-input]', files(PPTX, MEMO));
  expect((await posted).status()).toBe(202);
  const id = page.url().match(RQ_ID)![0];
  const again = page.waitForResponse((r) => r.request().method() === 'GET' && r.url().endsWith(`/api/requirements/v1/requirements/${id}`));
  await page.reload();
  // 브라우저가 응답 본문을 이미 버렸으면(다시 그리며 요청이 이어질 때) API 로 같은 시점 상태를 읽는다
  const snap = ((await (await again).json().catch(() => null)) ?? (await apiJson<Rq>(request, 'GET', `/requirements/${id}`))) as Rq;
  await expect(page.locator('.rq-filechip')).toHaveCount(2);
  if (snap.active_job) {
    // 다시 그린 화면이 진행을 이어 보여 준다(칩 상태 · 채우는 중 · a / b)
    await expect(page.getByTestId('fill-progress')).toContainText('채우는 중');
    await expect(page.locator('.rq-filechip[data-state="reading"], .rq-filechip[data-state="done"]')).toHaveCount(2);
  } else {
    test.info().annotations.push({ type: 'note', description: '새로고침보다 채우기가 먼저 끝났어요(진행 표시는 확인 못 함)' });
  }
  await expect(page.getByRole('button', { name: '파일 첨부' })).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('.rq-filechip[data-state="done"]')).toHaveCount(2);
  await expect(page.locator('#f-proj')).toHaveValue('용산 업무시설 재개발 AI Ready 오피스');
  await expect(page.getByTestId('km-count')).toHaveText('3명');
  await expect(page.getByRole('button', { name: '심층 작성' })).not.toHaveAttribute('aria-disabled', 'true');
});

test('E2E 4 가중치: 스테퍼 · 경계 끌기 · 합 100', async ({ page, request }) => {
  const U = uniq();
  const rq = await createRq(request, [
    { op: 'set_field', field: 'customer_name', value: `가중치고객${U}` },
    { op: 'add_keyman', name: '대표이사' }, { op: 'add_keyman', name: '공간컨텐츠실장' }, { op: 'add_keyman', name: '개발사업팀장' },
  ]);
  expect(rq.form.keymen.map((k) => k.weight)).toEqual([34, 33, 33]);
  await page.goto(`/requirements/${rq.id}/form`);
  await expect(page.getByTestId('equal-badge')).toHaveText('균등');
  expect(await weightsOf(page)).toEqual([34, 33, 33]);

  await page.getByRole('button', { name: '대표이사 가중치 높이기' }).click();
  await expect(page.getByTestId('stepper-대표이사')).toContainText('35%');
  await expect(page.locator('.rq-rightcard .rq-wbar__seg').first()).toHaveText('35%');
  expect(sum(await weightsOf(page))).toBe(100);
  await expect(page.getByTestId('equal-badge')).toHaveCount(0);
  await expect.poll(async () => (await apiJson<Rq>(request, 'GET', `/requirements/${rq.id}`)).form.weights_mode).toBe('custom');

  // 막대 경계 끌기(1% 단위) — 대표이사 · 공간컨텐츠실장 경계를 오른쪽으로
  const handle = page.getByRole('button', { name: '대표이사 · 공간컨텐츠실장 경계' });
  const box = (await handle.boundingBox())!;
  const barW = (await page.locator('.rq-rightcard .rq-wbar').first().boundingBox())!.width;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + barW * 0.1, box.y + box.height / 2, { steps: 6 });
  await page.mouse.up();
  await expect.poll(async () => (await weightsOf(page))[0]).toBeGreaterThan(35);
  const after = await weightsOf(page);
  expect(sum(after)).toBe(100);
  expect(after[2]).toBe(32);
  expect(Math.min(...after)).toBeGreaterThanOrEqual(5);
  await shot(page, 'rq2-weights');

  // 서버에도 같은 값(새로고침)
  await expect.poll(async () => (await apiJson<Rq>(request, 'GET', `/requirements/${rq.id}`)).form.keymen.map((k) => k.weight)).toEqual(after);
  await page.reload();
  expect(await weightsOf(page)).toEqual(after);
});

test('E2E 14 Storyboard 반영 줄: 미리 보기 · 저장 때 requirement-sync', async ({ page, request }) => {
  test.setTimeout(120_000);
  const U = uniq();
  const base = await createRq(request, []);
  const rq = await fillWith(request, base.id, [PPTX, MEMO]);
  const space = rq.form.keymen.find((k) => k.name === '공간컨텐츠실장')!;
  const item = space.items.find((i) => i.text.includes('업무환경 플랫폼'))!;
  const sbId = fakeId('sb');
  await apiJson(request, 'POST', `/requirements/${rq.id}/customer-questions`, {
    text: "'업무환경 플랫폼'에 어떤 서비스가 들어가나요?", keyman_id: space.id, target: { kind: 'item', id: item.id },
    origin: { kind: 'storyboard', feature: 'SB', service: 'storyboard', ref_id: sbId, place_label: '2-1 업무환경' },
  });
  await apiJson(request, 'POST', `/requirements/${rq.id}/save`, {});
  // 소비 서비스(storyboard) 대신 링크 등록 — internal 경로라 서비스에 직접
  const put = await request.put(`http://127.0.0.1:5101/v1/requirements/${rq.id}/links/storyboard/${sbId}`, {
    headers: { 'X-Internal-Token': internalToken(), 'X-User-Id': 'u_dev', 'X-Caller-Service': 'storyboard' },
    data: {
      title: '용산 업무시설 Storyboard', route: `/storyboard/${sbId}`, rq_version: 1,
      depends_on: [{ target: { kind: 'item', id: item.id }, places: [{ code: '2-1', label: '업무환경 플랫폼' }, { code: '3-2', label: '입주사 경험' }] }],
    },
  });
  expect(put.ok(), await put.text()).toBeTruthy();

  const syncCalls: Array<{ url: string; body: Record<string, unknown> }> = [];
  await page.route('**/api/storyboard/v1/storyboards/*/requirement-sync', async (route) => {
    syncCalls.push({ url: route.request().url(), body: route.request().postDataJSON() as Record<string, unknown> });
    await route.fulfill({ status: 202, json: { job_id: 'job_e2e', status: 'queued', ref: { kind: 'storyboard', id: sbId } } });
  });

  await page.goto(`/requirements/${rq.id}/reply`);
  await page.getByLabel('붙여 넣은 고객 답변').fill('1. 업무환경 플랫폼은 입주사 앱, 공용 공간 예약, 방문객 안내를 생각하고 있습니다.');
  await page.getByRole('button', { name: '바뀌는 곳 찾기' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/\d+곳이 바뀌어요/, { timeout: 30_000 });
  const line = page.getByTestId('storyboard-line');
  await expect(line).toContainText('Storyboard 2곳에도 반영');
  await expect(line.getByRole('checkbox')).toBeChecked();
  await expect(line.getByRole('link', { name: '미리 보기' })).toHaveAttribute('href', new RegExp(`/storyboard/${sbId}/versions\\?preview_rq=${rq.id}&reply=rp_`));
  await shot(page, 'rq7b-storyboard');

  await page.getByRole('button', { name: 'v2로 저장' }).click();
  await expect(page.getByTestId('doc-version')).toHaveText('정의서 v2');
  await expect.poll(() => syncCalls.length).toBe(1);
  expect(syncCalls[0].url).toContain(`/storyboards/${sbId}/requirement-sync`);
  expect(syncCalls[0].body).toMatchObject({ requirement_id: rq.id, to_version: 2, dry_run: false });
  const links = await apiJson<{ items: Array<{ ref_id: string; sync_state: string; pending_version: number | null }> }>(request, 'GET', `/requirements/${rq.id}/links`);
  expect(links.items.find((l) => l.ref_id === sbId)).toMatchObject({ sync_state: 'pending', pending_version: 2 });
});

test('E2E 15 사이드바 · 이어서: 심층 작성 중 다른 화면 → 사이드바 항목 → 질의(현재 번호)', async ({ page, request }) => {
  test.setTimeout(120_000);
  const U = uniq();
  const cust = `사이드바고객${U}`;
  const rq = await createRq(request, [
    { op: 'set_field', field: 'customer_name', value: cust }, { op: 'set_field', field: 'project_name', value: '심층 확인' },
    { op: 'add_keyman', name: '대표이사' }, { op: 'add_keyman', name: '개발사업팀장' },
  ]);
  const acc = await apiJson<{ ref: { id: string } }>(request, 'POST', `/requirements/${rq.id}/deep-sessions`);
  const sid = acc.ref.id;
  const ready = await waitSession(request, rq.id, sid);
  const started = await apiJson<Session>(request, 'POST', `/requirements/${rq.id}/deep-sessions/${sid}/start`);
  expect(started.status).toBe('asking');
  const N = started.total;
  expect(N).toBeGreaterThanOrEqual(2);
  await apiJson(request, 'POST', `/requirements/${rq.id}/deep-sessions/${sid}/answers`, { gap_id: started.current_gap_id, kind: 'skip' });
  expect(ready.status).toBe('ready');

  await page.goto(`/requirements/${rq.id}/deep/${sid}/q`);
  await expect(page.getByTestId('ask-progress')).toHaveText(`2 / ${N}`);
  await page.goto('/');
  const nav = page.getByRole('navigation', { name: '작업 내역' });
  await nav.getByRole('button', { name: '고객 요구사항 펼치기' }).click();
  await nav.getByRole('link', { name: `${cust} 심층 확인` }).click();
  await expect(page).toHaveURL(new RegExp(`/requirements/${rq.id}/deep/${sid}/q$`));
  await expect(page.getByTestId('ask-progress')).toHaveText(`2 / ${N}`);

  await page.goto(`/requirements/legacy?q=${encodeURIComponent(cust)}`);
  const row = page.getByRole('table', { name: '요구사항 목록' }).getByRole('row').filter({ hasText: cust });
  await expect(row.locator('.rq-pill')).toHaveText(`심층 작성 2 / ${N}`);
  await row.getByRole('link', { name: '이어서' }).click();
  await expect(page).toHaveURL(new RegExp(`/requirements/${rq.id}/deep/${sid}/q$`));
});
