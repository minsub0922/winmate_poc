/**
 * SP3 수정 요청 → SP3W(경고) → 나중에 → 표 위 경고 줄 → 선택한 대로 반영 — 06-spec §4.11 · §9.9(69 · 72 · 73 · 77 · 78).
 * kb 어댑터에는 QM55R 이 없어 `카탈로그 없음`(not_in_catalog) 카드가 생긴다(§9.9-78).
 * 목 sp.interpret_request 는 응답 두 개(연간 전기료 행 · QM55R 추가)를 번갈아 내므로, 버리는 시트로 순서를 맞춘 뒤 요청한다.
 */
import { expect, test, type APIRequestContext } from '@playwright/test';
import { QB55C, QM55C, api, generatedSheet, shot, waitIdle } from './helpers';

async function waitJob(request: APIRequestContext, jobId: string) {
  for (let i = 0; i < 80; i++) {
    const r = await request.get(`/api/jobs/v1/jobs/${jobId}`);
    const j = await r.json();
    if (['succeeded', 'failed', 'canceled'].includes(j.status)) return j;
    await new Promise((res) => setTimeout(res, 400));
  }
  throw new Error('잡이 끝나지 않음');
}

/** 다음 sp.interpret_request 응답이 `QM55R 추가` 가 되도록 맞춘다(번갈아 나오는 목) */
async function alignInterpretMock(request: APIRequestContext) {
  const tmp = await generatedSheet(request, [QM55C]);
  for (let i = 0; i < 3; i++) {
    const r = await api(request, 'POST', `/sheets/${tmp.id}/messages`, { text: '맞추기', context: 'result' });
    const j = await waitJob(request, r.job_id);
    await waitIdle(request, tmp.id);
    if (String(j.result?.reply ?? '').includes('연간 전기료')) return;
  }
  throw new Error('목 순서를 맞추지 못함');
}

test('기존 장비 추가 요청 → 경고 확인 → 반영', async ({ page, request }) => {
  const s = await generatedSheet(request, [QM55C, QB55C]);
  await alignInterpretMock(request);

  await page.goto(`/spec/${s.id}`);
  await page.getByLabel('수정 요청').fill('고객 매장 기존 장비 QM55R도 같이 비교해줘');
  await page.getByLabel('수정 요청').press('Enter');
  await expect(page.getByTestId('sp-user')).toHaveText('고객 매장 기존 장비 QM55R도 같이 비교해줘');
  await expect(page).toHaveURL(new RegExp(`/spec/${s.id}/warnings`), { timeout: 30_000 });

  await expect(page.getByText('최신 카탈로그와 다시 대조했어요. QM55R은 카탈로그에 없는 모델이에요.', { exact: false })).toBeVisible();
  const table = page.getByTestId('sp-warn-table');
  await expect(table).toContainText('Smart Signage 55" 비교 — 기존 장비 포함');
  await expect(table).toContainText('경고 1');
  await expect(table.locator('.sp-wt__col--existing')).toContainText('QM55R');
  await expect(table.locator('.sp-wt__col--existing')).toContainText('고객 기존 장비');
  await expect(page.getByTestId('sp-warn-footer')).toHaveText(/^출처: 사내 제품 카탈로그 \S+ 대조 · 시트 생성 \d{4}-\d{2}-\d{2}$/);
  await expect(table).toContainText('번호 = 오른쪽 경고');

  const panel = page.getByRole('complementary', { name: '확인이 필요한 곳' });
  await expect(panel.getByRole('button', { name: '전체 1' })).toHaveAttribute('aria-pressed', 'true');
  await expect(panel.getByRole('button', { name: '단종 1' })).toBeVisible();
  await expect(panel.getByRole('button', { name: '값 불일치 0' })).toBeVisible();
  await expect(panel.getByRole('button', { name: '요구 미충족 0' })).toBeVisible();
  const card = panel.getByTestId('sp-warning');
  await expect(card).toHaveCount(1);
  await expect(card).toContainText('QM55R · 고객 기존 장비');
  await expect(card).toContainText('사내 카탈로그에서 찾을 수 없는 모델이에요. 단종됐거나 아직 등록되지 않았을 수 있어요.');
  await expect(card.getByRole('radio', { name: "'기존 장비'로 표기하고 유지 — 교체 전 ↔ 후 비교" })).toHaveAttribute('aria-checked', 'true');
  await expect(panel.getByTestId('sp-decided')).toHaveText('결정 1 / 1');
  await expect(page.getByTestId('sp-dock-title')).toHaveText('Spec 시트 · 3 / 3 · 경고 확인 중');
  await shot(page, 'SP3W');

  // 카드 선택 → ?w= · 칸 실선
  await card.locator('.sp-wc__title').click();
  await expect(page).toHaveURL(/\?w=swn_/);
  await expect(table.locator('[data-sel="true"]').first()).toBeVisible();

  // 나중에 → SP3, 표 위 `확인이 필요한 곳 1 · 보기`
  await panel.getByRole('button', { name: '나중에' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${s.id}$`));
  await expect(page.getByTestId('sp-warnline')).toHaveText(/확인이 필요한 곳 1 · 보기/);
  await page.getByTestId('sp-warnline').getByRole('link', { name: '보기' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${s.id}/warnings`));

  // 수정 요청(경고 화면) → 열 이름 바꾸기(목 sp.interpret_request_warnings)
  await page.getByLabel('수정 요청').fill("QM55R 열 이름을 '기존 장비'로");
  await page.getByLabel('수정 요청').press('Enter');
  await expect(table.locator('.sp-wt__col--existing .sp-wt__name b')).toHaveText('기존 장비', { timeout: 20_000 });

  // 선택한 대로 반영(기본 선택) → SP3, 열은 고객 기존 장비로 유지
  await panel.getByRole('button', { name: '선택한 대로 반영' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${s.id}$`));
  const after = await api(request, 'GET', `/sheets/${s.id}`);
  const r55 = (after.products as Array<{ display_name: string; role: string }>).find((p) => p.display_name === 'QM55R');
  expect(r55?.role).toBe('existing');
  expect(after.warnings.open).toBe(0);
  await expect(page.getByTestId('sp-warnline')).toHaveCount(0);
});
