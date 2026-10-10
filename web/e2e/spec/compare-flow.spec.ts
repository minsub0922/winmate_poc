/**
 * SP0 → SP1 → SP2 → SP3G → SP3 — 모델명 두 개로 비교표(06-spec §3.1 · §9.1 · §9.2 · §9.5 · §9.7 · §9.8).
 * 값은 kb 실데이터(QM55C 500 nit · QB55C 350 nit · 24/7 vs 16/7). 소비전력(일반 · 최대) · 보증은 kb 에 없어 값 확인으로 묻는다.
 */
import { expect, test } from '@playwright/test';
import { QM55C, api, createSheet, ready, shot } from './helpers';

async function addModel(page: import('@playwright/test').Page, q: string) {
  const box = page.getByRole('combobox');
  await box.fill(q);
  const opt = page.getByRole('listbox', { name: '제품 검색 결과' }).getByRole('option').filter({ hasText: q }).first();
  await expect(opt).toBeVisible({ timeout: 10_000 });
  await opt.click();
}

test('모델명 두 개 → 항목 · 형식 → 생성 · 값 확인 → 결과', async ({ page, request }) => {
  // SP0(이전 흐름 목록 — 새 흐름 목록은 /spec · sp-flow.spec.ts)
  await page.goto('/spec/legacy');
  await expect(page.getByRole('heading', { name: 'Spec 시트 작업' })).toBeVisible();
  await expect(page.getByText('모델명으로 입력')).toBeVisible();
  await expect(page.getByText('조건으로 모델 찾기').first()).toBeVisible();
  await shot(page, 'SP0');

  // SP1
  await page.getByRole('button', { name: '새 Spec 시트' }).click();
  await expect(page).toHaveURL(/\/spec\/legacy\/new$/);
  await ready(page);
  await expect(page.getByText('스펙 시트를 만들 제품을 입력해 주세요.', { exact: false })).toBeVisible();
  await expect(page.getByTestId('sp-dock-title')).toHaveText('제품 입력 · 1 / 3');
  await expect(page.getByRole('button', { name: '항목 · 형식 선택' })).toBeDisabled();
  await addModel(page, 'QM55C');
  await expect(page).toHaveURL(/\/spec\/sp_[A-Z0-9]+\/products/);
  await addModel(page, 'QB55C');
  await expect(page.getByTestId('sp-dock-title')).toHaveText('제품 입력 · 2개 추가됨 · 1 / 3');
  await shot(page, 'SP1');
  const id = page.url().match(/\/spec\/(sp_[A-Z0-9]+)/)![1];

  // SP2
  await page.getByRole('button', { name: '항목 · 형식 선택' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${id}/items$`));
  await expect(page.getByTestId('sp-user')).toHaveText('제품 2개 · Smart Signage QM55C / QB55C');
  await expect(page.getByText('두 모델은 같은 55" 4K 사이니지지만 밝기(500 vs 350nit)와 운영 시간(24/7 vs 16/7)이 다릅니다. 시트에 넣을 스펙 항목과 출력 형식을 골라주세요.')).toBeVisible();
  await expect(page.getByTestId('sp-dock-title')).toHaveText('스펙 항목 · 7개 선택 · 2 / 3');
  const items = page.getByRole('group', { name: '스펙 항목' }).getByRole('button');
  await expect(items).toHaveCount(12);
  for (const on of ['화면 크기 · 해상도', '밝기 · 명암비', '운영 시간', '소비전력 (일반 · 최대)', '내장 플레이어 · OS', 'MagicINFO 호환', '보증']) {
    await expect(items.filter({ hasText: on })).toHaveAttribute('aria-pressed', 'true');
  }
  for (const off of ['입출력 단자', '크기 · 무게', '베젤', '인증', '액세서리']) {
    await expect(items.filter({ hasText: off })).toHaveAttribute('aria-pressed', 'false');
  }
  await expect(page.getByRole('button', { name: '비교표' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: '한국어' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: '우위 항목 하이라이트' })).toHaveAttribute('aria-pressed', 'true');
  await shot(page, 'SP2');

  // 차이 있는 항목만 → 밝기 · 운영 시간은 켬, 화면 크기는 끔
  await page.getByRole('button', { name: '차이 있는 항목만' }).click();
  await expect(items.filter({ hasText: '밝기 · 명암비' })).toHaveAttribute('aria-pressed', 'true');
  await expect(items.filter({ hasText: '운영 시간' })).toHaveAttribute('aria-pressed', 'true');
  await expect(items.filter({ hasText: '화면 크기 · 해상도' })).toHaveAttribute('aria-pressed', 'false');
  await page.getByRole('button', { name: '전체 선택' }).click();
  await expect(page.getByTestId('sp-dock-title')).toHaveText('스펙 항목 · 12개 선택 · 2 / 3');
  // 기본 7개로 되돌림
  for (const off of ['입출력 단자', '크기 · 무게', '베젤', '인증', '액세서리']) await items.filter({ hasText: off }).click();
  await expect(page.getByTestId('sp-dock-title')).toHaveText('스펙 항목 · 7개 선택 · 2 / 3');

  // SP3G
  await page.getByRole('button', { name: '시트 생성', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${id}/generating\\?job=job_`));
  await expect(page.getByTestId('sp-user')).toHaveText('QM55C · QB55C · 항목 7개 · 비교표 · 한국어');
  await expect(page.getByText('사내 카탈로그에서 두 모델의 스펙을 채우고 있어요.', { exact: false })).toBeVisible();
  await expect(page.getByTestId('sp-progress-title')).toHaveText(/시트 생성 완료 · 값 확인 필요 4/, { timeout: 30_000 });
  await expect(page.locator('[data-step="resolve_models"]')).toContainText('사내 카탈로그 매칭 2 / 2');
  await expect(page.locator('[data-step="fetch_specs"]')).toContainText('14칸 중 10칸 채움');
  await expect(page.locator('[data-step="verify"]')).toContainText('4곳 확인 필요');
  await expect(page.getByTestId('sp-dock-title')).toHaveText('Spec 시트 · 3 / 3 · 값 확인');
  const checks = page.getByTestId('sp-check');
  await expect(checks).toHaveCount(4);
  await expect(checks.nth(0)).toContainText('소비전력 (일반 · 최대) · QM55C');
  await expect(checks.nth(0)).toContainText('사내 카탈로그에 값이 없어요. 데이터시트가 있으면 읽어서 채울게요.');
  await expect(checks.nth(0).getByLabel('소비전력 값 입력')).toHaveAttribute('placeholder', '값 입력 · W');
  await expect(checks.nth(0).getByRole('button', { name: 'On Mode · 154 W' })).toBeVisible();
  await shot(page, 'SP3G');

  // 단위가 틀린 값 → 422 INVALID_VALUE
  const pw2 = checks.nth(1).getByLabel('소비전력 값 입력');
  await pw2.fill('100 kWh');
  await pw2.press('Enter');
  await expect(checks.nth(1).getByRole('alert')).toHaveText('W 단위로 넣어 주세요.');
  await pw2.fill('100 / 150');
  await pw2.press('Enter');
  await expect(checks.nth(1).getByRole('alert')).toHaveCount(0);
  await checks.nth(0).getByRole('button', { name: 'On Mode · 154 W' }).click();
  await expect(checks.nth(0).getByRole('button', { name: 'On Mode · 154 W' })).toHaveAttribute('aria-pressed', 'true');

  // 답 반영하고 완성 → SP3(열린 경고 없음)
  await page.getByRole('button', { name: '답 반영하고 완성' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${id}$`), { timeout: 15_000 });
  await expect(page.getByText('비교표가 완성되었습니다. 파란 셀은 우위 항목입니다. 셀을 클릭하면 값을 직접 고칠 수 있고, 출처는 사내 카탈로그', { exact: false })).toBeVisible();
  await expect(page.getByTestId('sp-sheet-title')).toHaveText('Smart Signage 55" 비교 — QM55C vs QB55C');
  const table = page.getByRole('table');
  await expect(table.getByRole('cell', { name: /500 nit · 4,000:1/ })).toHaveAttribute('data-win', 'true');
  await expect(table.getByRole('cell', { name: /100 W · 150 W/ })).toHaveAttribute('data-state', 'edited');
  await expect(page.getByTestId('sp-win-count')).toHaveText(/우위 항목 \d/);
  await expect(page.getByTestId('sp-source-line')).toContainText('출처: 사내 제품 카탈로그');
  await expect(page.getByTestId('sp-dock-title')).toHaveText('Spec 시트 · 3 / 3 · 완료');
  await shot(page, 'SP3');

  // 셀 직접 고치기(Enter 저장) → edited
  await table.getByRole('cell', { name: /QM55C 값 고치기: 24\/7/ }).click();
  const input = table.getByRole('textbox');
  await input.fill('18/7');
  await input.press('Enter');
  await expect(table.getByRole('cell', { name: /18\/7/ })).toHaveAttribute('data-state', 'edited');

  // 저장 → version +1 · saved_at
  const before = await api(request, 'GET', `/sheets/${id}`);
  await page.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByText('저장했어요.')).toBeVisible();
  const after = await api(request, 'GET', `/sheets/${id}`);
  expect(after.version).toBe(before.version + 1);
  expect(after.saved_at).toBeTruthy();
  expect(after.ui_status).toBe('done');
});

test('SP1Product — 제품 탐색 팝오버(셸)는 작업이 있는 상태로 열린다', async ({ page, request }) => {
  const { id } = await createSheet(request, [QM55C]);
  await page.goto(`/spec/${id}/products`);
  await expect(page.getByTestId('sp-dock-title')).toHaveText('제품 입력 · 1개 추가됨 · 1 / 3');
  await page.getByRole('button', { name: '제품 탐색에서 고르기' }).click();
  await expect(page).toHaveURL(/pop=product/);
  const dlg = page.getByRole('dialog', { name: '제품 탐색' });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByText('진행 중인 작업이 없어 탐색만 할 수 있어요.', { exact: false })).toHaveCount(0);
  await shot(page, 'SP1Product');
});
