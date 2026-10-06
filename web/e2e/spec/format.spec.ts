/**
 * SP2L — 출력 형식 · 언어 · 단위(06-spec §4.8 · §4.16 · §4.18 · §9.6).
 * kb 실데이터 치수 · 무게(mm · kg)를 inch · lb 로 바꾼 미리보기, 내 기본값 저장, 고객사 양식 올리기.
 */
import { expect, test } from '@playwright/test';
import { QB55C, QM55C, api, createSheet, fileBuffer, generatedSheet, shot } from './helpers';

const SYSTEM_DEFAULTS = { formats: ['xlsx'], language: 'ko', length_unit: 'mm', weight_unit: 'kg', paper: 'a4_landscape', number_format: '1,234.5' };

test('형식 · 언어 · 단위 미리보기와 내 기본값', async ({ page, request }) => {
  const { id } = await createSheet(request, [QM55C, QB55C]);
  await api(request, 'PATCH', `/sheets/${id}`, { step: 2 });
  await api(request, 'PUT', `/sheets/${id}/items`, { items: [{ key: 'size_weight', checked: true }] });

  await page.goto(`/spec/${id}/items`);
  await page.getByRole('link', { name: '언어 · 단위 자세히' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${id}/format\\?from=items`));
  await expect(page.getByText('출력 형식과 언어 · 단위를 골라 주세요. 고객사 양식이 있으면 올려 주세요. 같은 칸 순서로 맞춰 드립니다.')).toBeVisible();
  await expect(page.getByTestId('sp-dock-title')).toHaveText('출력 형식 · 언어 · 단위 · 2 / 3');

  const group = (g: string) => page.getByRole('group', { name: g });
  await group('형식').getByRole('button', { name: 'PDF' }).click();
  await group('언어').getByRole('button', { name: 'English' }).click();
  await group('길이').getByRole('button', { name: 'inch' }).click();
  await group('무게').getByRole('button', { name: 'lb' }).click();

  const prev = page.getByTestId('sp-format-preview');
  await expect(page.getByTestId('sp-format-chip')).toHaveText('English · inch · lb');
  await expect(prev.getByRole('tab', { name: 'Excel (.xlsx)' })).toHaveAttribute('data-state', 'on');
  await expect(prev.getByRole('tab', { name: 'PDF · A4 가로' })).toHaveAttribute('data-state', 'sel');
  await expect(prev.getByRole('tab', { name: 'PPT 슬라이드' })).toHaveAttribute('data-state', 'off');
  await expect(prev.locator('[data-row="1"]')).toHaveText(/Samsung Smart Signage 55" Comparison/);
  await expect(prev.locator('[data-row="2"]')).toContainText('Item');
  const dims = prev.locator('.sp-fp__r', { hasText: 'Dimensions (W × H × D)' });
  await expect(dims.locator('[data-converted="true"]').first()).toHaveText(/^\d+\.\d × \d+\.\d × \d+\.\d in$/);
  await expect(prev.locator('.sp-fp__r', { hasText: 'Weight (Set / Package)' }).locator('[data-converted="true"]').first()).toHaveText(/lb/);
  await expect(prev.locator('[data-converted="true"]')).toHaveCount(4);
  await expect(page.getByTestId('sp-format-note')).toHaveText('단위 바뀐 셀 4개 · 소수점 첫째 자리 반올림 · mm 원래 값은 셀 메모에 보관');
  await expect(prev.getByText('Comparison', { exact: true })).toBeVisible();
  await expect(prev.getByText('Notes & Sources')).toBeVisible();
  await expect(page.getByLabel('파일명')).toHaveValue('Samsung_Signage_55_Comparison_EN');
  await expect(page.locator('.sp-fname span')).toHaveText('.xlsx · .pdf');
  await shot(page, 'SP2L');

  // 무게만 lb → 원래 단위 kg
  await group('길이').getByRole('button', { name: 'mm', exact: true }).click();
  await expect(page.getByTestId('sp-format-note')).toHaveText('단위 바뀐 셀 2개 · 소수점 첫째 자리 반올림 · kg 원래 값은 셀 메모에 보관');
  // 숫자 1.234,5 · inch → 소수점 쉼표
  await group('길이').getByRole('button', { name: 'inch' }).click();
  await group('숫자').getByRole('button', { name: '1.234,5' }).click();
  await expect(dims.locator('[data-converted="true"]').first()).toHaveText(/^\d+,\d × \d+,\d × \d+,\d in$/);
  await group('숫자').getByRole('button', { name: '1,234.5' }).click();
  // PDF 탭 · 용지 Letter
  await group('용지').getByRole('button', { name: 'Letter' }).click();
  await expect(prev.getByRole('tab', { name: 'PDF · Letter' })).toBeVisible();
  await prev.getByRole('tab', { name: 'PDF · Letter' }).click();
  await expect(prev.getByRole('tab', { name: 'PDF · Letter' })).toHaveAttribute('data-state', 'on');
  // PPT 만 → 확장자 .pptx
  await group('형식').getByRole('button', { name: 'PPT 슬라이드' }).click();
  await group('형식').getByRole('button', { name: 'Excel' }).click();
  await group('형식').getByRole('button', { name: 'PDF' }).click();
  await expect(page.locator('.sp-fname span')).toHaveText('.pptx');
  await group('형식').getByRole('button', { name: 'Excel' }).click();
  await group('형식').getByRole('button', { name: 'PDF' }).click();
  await group('형식').getByRole('button', { name: 'PPT 슬라이드' }).click();
  await group('용지').getByRole('button', { name: 'A4 가로' }).click();

  // 내 기본값으로 저장 → 새 작업의 SP2 언어 칩이 English 로 시작
  try {
    await page.getByRole('button', { name: '내 기본값으로 저장' }).click();
    await expect(page.getByRole('button', { name: '내 기본값으로 저장됨' })).toBeVisible();
    const prefs = await api(request, 'GET', '/preferences');
    expect(prefs.format).toMatchObject({ formats: ['xlsx', 'pdf'], language: 'en', length_unit: 'inch', weight_unit: 'lb', paper: 'a4_landscape', number_format: '1,234.5' });
    const other = await createSheet(request, [QM55C]);
    await api(request, 'PATCH', `/sheets/${other.id}`, { step: 2 });
    await page.goto(`/spec/${other.id}/items`);
    await expect(page.getByRole('button', { name: 'English' })).toHaveAttribute('aria-pressed', 'true');
    // 단일 제품: 형식 · 차이 강조 줄과 `차이 있는 항목만` 이 없다(§9.5-40)
    await expect(page.getByRole('button', { name: '차이 있는 항목만' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: '비교표' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: '우위 항목 하이라이트' })).toHaveCount(0);
  } finally {
    await api(request, 'PUT', '/preferences', SYSTEM_DEFAULTS);
  }

  // 시트 생성(아직 생성 전) → generate → SP3G
  await page.goto(`/spec/${id}/format?from=items`);
  await expect(page.getByTestId('sp-format-chip')).toBeVisible();
  await page.getByRole('button', { name: '시트 생성', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${id}/generating\\?job=job_`));
  const saved = await api(request, 'GET', `/sheets/${id}`);
  expect(saved.format_confirmed).toBe(true);
});

test('영문 버전(SP3 → SP2L) · 고객사 양식 올리기', async ({ page, request }) => {
  const s = await generatedSheet(request, [QM55C, QB55C]);
  await page.goto(`/spec/${s.id}`);
  await page.getByRole('button', { name: '영문 버전' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${s.id}/format\\?from=result&en=1`));
  await expect(page.getByTestId('sp-format-chip')).toHaveText('English · inch · lb');
  await expect(page.getByText('Excel로 만들고 영문 · inch · lb 기준으로 바꿨습니다. 단위가 바뀐 셀은 파랗게 표시했어요.', { exact: false })).toBeVisible();
  // 저장은 사용자가 — 아직 시트 형식은 그대로
  expect((await api(request, 'GET', `/sheets/${s.id}`)).format.language).toBe('ko');

  // 고객사 양식(XLSX) → spec_template(목 sp.template_map) → 미리보기 행이 양식 순서 · 이름
  await page.locator('input[type=file][aria-label="고객사 양식 파일"]').setInputFiles(
    fileBuffer('고객사_스펙양식.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'));
  const chip = page.getByTestId('sp-template-chip');
  await expect(chip).toContainText('고객사 양식 · 고객사_스펙양식.xlsx');
  await expect(chip).not.toContainText('맞추는 중', { timeout: 30_000 });
  const prev = page.getByTestId('sp-format-preview');
  await expect(prev).toContainText('Remarks', { timeout: 15_000 });
  await shot(page, 'SP2L-template');

  // 이전 → SP3(들어온 곳)
  await page.getByRole('button', { name: '이전' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/${s.id}$`));
});
