/**
 * 다른 기능의 요청(AC54) · 제안서에 넣기(AC53, 제안서 계약이 아직 없어 page.route 로 흉내) · 갤러리 다중 선택.
 */
import { expect, test } from '@playwright/test';
import { api, doneWork, shot, uniq } from './helpers';

test('시나리오 요청 → IMG0 「만들기」 → IMG1 미리 채움 → IMG4 「공간 시나리오 장면으로」 충족(AC54)', async ({ page, request }) => {
  test.setTimeout(150_000);
  const tag = uniq();
  const req = await api(request, 'POST', '/requests', {
    from_service: 'scenario', from_ref: `scn_e2e_${tag}`, from_label: `공간 시나리오 · A 커피 매장 하루 ${tag}`, title: `장면 2 · 점심 피크 주문 ${tag}`,
    prefill: { kind: 'scenario', description: '점심 피크 시간, 카운터 앞에서 손님이 주문하는 장면', products: ['QM55C'], aspect: '16:9' },
  }, 'scenario');
  await page.goto('/image');
  const row = page.getByTestId('img0-request').filter({ hasText: `장면 2 · 점심 피크 주문 ${tag}` });
  await expect(row).toContainText(`공간 시나리오 · A 커피 매장 하루 ${tag}`);
  await shot(page, 'IMG0-requests');
  await row.getByRole('button', { name: '만들기' }).click();
  await expect(page).toHaveURL(/\/image\/new\?work=imw_/);
  await expect(page.getByRole('radio', { name: /시나리오/ })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByLabel('장면 설명')).toHaveValue('점심 피크 시간, 카운터 앞에서 손님이 주문하는 장면');
  const workId = new URL(page.url()).searchParams.get('work')!;
  const st = await api(request, 'GET', `/requests/${req.id}`);
  expect([st.status, st.work_id]).toEqual(['in_progress', workId]);

  // 만들고 IMG4 에서 「공간 시나리오 장면으로」
  await page.getByRole('button', { name: '상세 조건 입력' }).click();
  await expect(page).toHaveURL(/\/conditions$/);
  await expect(page.getByTestId('img-prodchip')).toContainText('QM55C');
  await page.getByRole('button', { name: '2장', exact: true }).click();
  await page.getByRole('button', { name: /이미지 2장 생성/ }).click();
  await expect(page.getByRole('button', { name: '결과 보기' })).toBeEnabled({ timeout: 90_000 });
  await page.getByRole('button', { name: '결과 보기' }).click();
  await page.getByRole('button', { name: /제안서에 넣기/ }).click();
  await expect(page).toHaveURL(/\/export\//);
  await page.getByRole('button', { name: '공간 시나리오 장면으로' }).click();
  await expect(page).toHaveURL(/\/scenario\?image_version=imv_/);
  const done = await api(request, 'GET', `/requests/${req.id}`);
  expect(done.status).toBe('fulfilled');
  expect(done.result_version_id).toMatch(/^imv_/);
});

test('제안서에 넣기 — 목록 · 추천 시트 · 가져오기 요청 본문(AC53, 제안서 흉내)', async ({ page, request }) => {
  test.setTimeout(120_000);
  const { work, run } = await doneWork(request, { count: 2 });
  const imageId = run.shots[0].image_id;
  const imports: unknown[] = [];
  await page.route('**/api/proposal/v1/proposals?**', (r) => r.fulfill({ json: { items: [
    { id: 'prp_e2e_a', title: 'A 커피 프랜차이즈 메뉴보드 제안', short_title: 'A 커피 제안서', meta: '표준 제안서 · 작성 중' },
    { id: 'prp_e2e_b', title: 'B 병원 안내 시스템 제안', short_title: 'B 병원 제안서', meta: '표준 제안서 · 검토 중' },
  ] } }));
  await page.route('**/api/proposal/v1/proposals/*/image-slots**', (r) => r.fulfill({ json: { sheets: [
    { sheet_id: 'sh_counter', name: '카운터 · 메뉴보드', section: '공간별 제품 · 같은 공간 장면', recommended: true, slots: 1 },
    { sheet_id: 'sh_vp', name: '가치 제안', section: 'Value Props', recommended: false, slots: 1 },
  ] } }));
  await page.route('**/api/proposal/v1/proposals/*/imports', async (r) => { imports.push(r.request().postDataJSON()); await r.fulfill({ status: 201, json: { id: 'imp_1' } }); });
  await page.goto(`/image/w/${work.id}/export/${imageId}`);
  await expect(page.getByRole('radio', { name: /A 커피 프랜차이즈 메뉴보드 제안/ })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByRole('radio', { name: /카운터 · 메뉴보드/ })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByRole('radio', { name: /카운터 · 메뉴보드/ })).toContainText('추천');
  await expect(page.getByTestId('img4-head')).toHaveText('내보내기 · A 커피 제안서 › 카운터 · 메뉴보드');
  await expect(page.getByRole('button', { name: '이미지 자리 교체' })).toHaveAttribute('aria-pressed', 'true');
  await shot(page, 'IMG4-proposal');
  await page.getByRole('button', { name: /제안서에 넣기/ }).click();
  await expect.poll(() => imports.length).toBe(1);
  const img = await api(request, 'GET', `/images/${imageId}`);
  expect(imports[0]).toEqual({ source: { service: 'image', version_id: img.current_version_id, image_id: imageId }, target: { sheet_id: 'sh_counter', mode: 'replace_slot' }, caption: null });
  await expect(page.getByText('A 커피 제안서 › 카운터 · 메뉴보드에 넣었어요')).toBeVisible();
});

test('진행 중인 제안서가 없으면 「새 제안서로 시작」', async ({ page, request }) => {
  const { work, run } = await doneWork(request, { count: 2 });
  await page.route('**/api/proposal/v1/proposals?**', (r) => r.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: '없음' } } }));
  await page.goto(`/image/w/${work.id}/export/${run.shots[0].image_id}`);
  await expect(page.getByTestId('img4-noprop')).toContainText('진행 중인 제안서가 없어요');
  await expect(page.getByTestId('img4-noprop').getByRole('link', { name: '새 제안서로 시작' })).toBeVisible();
});

test('갤러리 다중 선택 → 다운로드(ZIP)', async ({ page, request }) => {
  test.setTimeout(120_000);
  const { run } = await doneWork(request, { count: 2 });
  for (const s of run.shots) await api(request, 'POST', `/images/${s.image_id}:save`);
  await page.goto('/image');
  for (const s of run.shots) await page.locator(`[data-testid="img0-tile"]:has(a[href*="${s.image_id}"])`).getByRole('checkbox').click();
  await expect(page.getByTestId('img0-selbar')).toContainText('2장 선택됨');
  await shot(page, 'IMG0-selected');
  const dl = page.waitForEvent('download', { timeout: 60_000 });
  await page.getByTestId('img0-selbar').getByRole('button', { name: '다운로드' }).click();
  const f = await dl;
  expect(f.url()).toContain('download=1');
  await page.getByTestId('img0-selbar').getByRole('button', { name: '선택 해제' }).click();
  await expect(page.getByTestId('img0-selbar')).toHaveCount(0);
});
