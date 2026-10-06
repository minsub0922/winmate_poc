/**
 * 제안서 기본 흐름(실제 proposal · 플랫폼 · mock 모델) — PR0 → PR1 → PR2 → PR3 → PR3I → 섹션(SectionStep · 템플릿 고르기) → PR6 → PR7 → PR7P → PR7X.
 * 공유 데이터라 이 테스트가 만든 제안서만 쓰고 끝나면 지운다.
 */
import { expect as baseExpect, test, type Page } from '@playwright/test';
import { CUSTOMER, PR_ID, api, backendDown, removeProposal, shot, isolateBrokenFeatures, open } from './helpers';

/** 공유 PC(2 CPU)에 다른 세션 테스트가 함께 돌아 느릴 수 있어 기다림을 넉넉히 */
const expect = baseExpect.configure({ timeout: 20_000 });

/** 흐름이라 순서대로(serial). 탭이 메모리 부족으로 죽으면(cgroup OOM) 흐름 전체를 새 제안서로 한 번 다시 돌린다 */
test.describe.configure({ mode: 'serial', timeout: 150_000, retries: 1 });
test.use({ actionTimeout: 30_000, navigationTimeout: 60_000 });
test.beforeEach(async ({ page }) => { await isolateBrokenFeatures(page); });
let id: string | null = null;

test.afterAll(async ({ request }) => { await removeProposal(request, id); });

async function sectionKeys(page: Page) {
  return page.getByTestId('pr-rail').getByRole('link').allTextContents();
}

test('PR0 → 빈 제안서 → PR1 자동 저장 → PR2 → PR3 → PR3I → 첫 섹션', async ({ page, request }) => {
  test.setTimeout(180_000);
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');

  await open(page, '/proposal');
  await expect(page.getByTestId('pr0')).toBeVisible();
  await expect(page.getByRole('heading', { name: '제안서' })).toBeVisible();
  await expect(page.getByTestId('pr0-summary')).toContainText('전체');
  for (const t of ['빈 제안서', 'RFP로 시작', '기존 작업에서 시작', '이전 제안서 복제']) await expect(page.getByText(t, { exact: true })).toBeVisible();
  await expect(page.getByRole('tab')).toHaveText([/전체/, /작성 중/, /검토 중/, /완료/]);
  await shot(page, 'flow-pr0');

  // 시작 방식이 정해지는 순간 제안서를 만든다(AC-002)
  await page.getByTestId('pr0-start-blank').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${PR_ID.source}/customer$`), { timeout: 15_000 });
  id = page.url().match(PR_ID)![0];
  await expect(page.getByTestId('pr1')).toBeVisible();
  await page.getByLabel('고객사').fill(CUSTOMER);
  await page.getByLabel('프로젝트명').fill('[e2e] 전국 매장 디지털 메뉴보드 전환');
  await page.getByRole('button', { name: '리테일 · F&B' }).click();
  await page.getByLabel('규모').fill('320개 매장');
  await shot(page, 'flow-pr1');
  // 0.8초 디바운스 자동 저장
  await expect.poll(async () => (await api(request, 'GET', `/proposals/${id}`)).customer?.name, { timeout: 10_000 }).toBe(CUSTOMER);
  const saved = await api(request, 'GET', `/proposals/${id}`);
  expect(saved.title).toBe('[e2e] 전국 매장 디지털 메뉴보드 전환');
  expect(saved.customer.scale_text).toBe('320개 매장');

  await page.getByTestId('pr1-next').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/type$`));
  await expect(page.getByTestId('pr2')).toBeVisible();
  for (const t of ['standard', 'quickwin', 'solution']) await expect(page.getByTestId(`pr2-type-${t}`)).toBeVisible();
  await expect(page.getByTestId('pr2-summary')).toContainText(CUSTOMER);
  await shot(page, 'flow-pr2');
  await page.getByTestId('pr2-type-standard').click();

  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/compose`));
  await expect(page.getByTestId('pr3-list')).toBeVisible();
  for (const k of ['mi', 'vp', 'birdseye', 'spaceProducts', 'solution', 'cases', 'why', 'spec']) await expect(page.getByTestId(`pr3-sec-${k}`)).toBeVisible();
  await shot(page, 'flow-pr3');
  expect((await api(request, 'GET', `/proposals/${id}`)).type).toBe('standard');

  // 업종(외식 · 카페)이 감지돼 있고 아직 정하지 않았으면 PR3I
  await page.getByTestId('pr3-start').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/(industry|sections/mi)`));
  if (page.url().includes('/industry')) {
    await expect(page.getByTestId('pr3i-detected')).toBeVisible();
    await expect(page.getByTestId('pr3i-label')).toContainText('외식');
    await expect(page.getByTestId('pr3i-stats')).toBeVisible();
    await expect(page.getByTestId('pr3i-fam-MI')).toBeVisible();
    await shot(page, 'flow-pr3i');
    await page.getByTestId('pr3i-apply').click();
  }
  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/sections/mi`));
  await expect(page.getByTestId('pr-section')).toBeVisible();
  await expect(page.getByTestId('pr-sheet-card').first()).toBeVisible();
  expect(await page.getByTestId('pr-sheet-card').count()).toBeGreaterThanOrEqual(3);
  await expect(page.getByTestId('pr-section-intro')).toContainText('Market Intelligence');
  expect((await sectionKeys(page)).length).toBeGreaterThanOrEqual(8);
  await shot(page, 'flow-prs1');
});

test('섹션: 템플릿 고르기 패널 → 직접 선택 고정 → 섹션 넘기기 → PR6', async ({ page, request }) => {
  test.setTimeout(180_000);
  test.skip(!id, '앞 테스트가 제안서를 만들지 못했어요');
  await open(page, `/proposal/${id}/sections/mi`);
  await page.getByTestId('pr-sheet-card').first().click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/sections/mi/sheets/sht_[^/]+/template$`));
  await expect(page.getByTestId('pr-template-panel')).toBeVisible();
  await expect(page.getByTestId('pr-template-rec')).toBeVisible();
  await shot(page, 'flow-prs1-layout');
  const sheetId = page.url().match(/sheets\/(sht_[^/]+)/)![1];
  await page.getByRole('radio', { name: '직접 선택' }).click();
  const variants = page.getByRole('radiogroup', { name: '템플릿' }).getByRole('radio');
  if (await variants.count() > 1) await variants.nth(1).click();
  await page.getByTestId('pr-template-apply').click();
  await expect.poll(async () => (await api(request, 'GET', `/proposals/${id}/sheets/${sheetId}`)).template.mode, { timeout: 10_000 }).toBe('pinned');

  // 섹션 8개를 「다음」으로 넘겨 PR6 까지(섹션 확정)
  await open(page, `/proposal/${id}/sections/mi`);
  for (let i = 0; i < 8; i += 1) {
    if (/\/design$/.test(page.url())) break;
    await expect(page.getByTestId('pr-section')).toBeVisible();
    await page.getByTestId('pr-sec-next').click();
    await page.waitForURL(/\/(sections\/[A-Za-z]+|design)$/, { timeout: 15_000 });
  }
  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/design$`));
  await expect(page.getByTestId('pr6')).toBeVisible();
  for (const n of ['삼성 B2B 표준', '리테일 · F&B 변형', '심플 화이트']) await expect(page.getByText(n, { exact: true })).toBeVisible();
  await shot(page, 'flow-pr6');
  const p = await api(request, 'GET', `/proposals/${id}`);
  expect(p.sections.filter((s: any) => s.enabled).every((s: any) => s.confirmed)).toBe(true);
});

test('PR6 → PPTX 생성 → PR7 결과 · PR7X 내보내기 모달', async ({ page, request }) => {
  test.setTimeout(240_000);
  test.skip(!id, '앞 테스트가 제안서를 만들지 못했어요');
  await open(page, `/proposal/${id}/design`);
  await expect(page.getByTestId('pr6')).toBeVisible();
  // HEX 검증
  await page.getByTestId('pr6-hex').fill('#12');
  await page.getByTestId('pr6-hex').press('Enter');
  await expect(page.getByText('#RRGGBB 형식으로 넣어 주세요')).toBeVisible();
  await page.getByTestId('pr6-hex').fill('#00704A');
  await page.getByTestId('pr6-hex').press('Enter');
  await expect.poll(async () => (await api(request, 'GET', `/proposals/${id}/design`)).design.brand_hex, { timeout: 10_000 }).toBe('#00704A');

  await page.getByTestId('pr6-generate').click();
  // 자료 없는 섹션이 있으면 추론으로 채울지 묻는다
  const dlg = page.getByRole('dialog');
  if (await dlg.isVisible().catch(() => false)) await dlg.getByRole('button', { name: '추론으로 채우고 만들기' }).click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/result$`), { timeout: 15_000 });
  await expect(page.getByTestId('pr7-file')).toBeVisible({ timeout: 180_000 });
  await expect(page.getByTestId('pr7-file-meta')).toContainText('슬라이드');
  expect(await page.getByTestId('pr7-thumbs').locator('a').count()).toBe(10);
  await expect(page.getByTestId('pr7-ranges')).toContainText('[수치 확정 필요]');
  await shot(page, 'flow-pr7');

  await page.getByTestId('pr7-export').click();
  await expect(page).toHaveURL(/export=1/);
  await expect(page.getByTestId('pr7x')).toBeVisible();
  await shot(page, 'flow-pr7x');
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('pr7x')).toBeHidden();
});

test('PR7P — 레일 · 큰 미리보기 · 표 행 고치기(PATCH + If-Match) · 발표자 노트', async ({ page, request }) => {
  test.setTimeout(120_000);
  test.skip(!id, '앞 테스트가 제안서를 만들지 못했어요');
  const slides = await api(request, 'GET', `/proposals/${id}/slides`);
  const all = slides.sections.flatMap((s: any) => s.sheets);
  const cm = all.find((s: any) => s.title === '경쟁 비교') ?? all[0];
  await open(page, `/proposal/${id}/preview/${cm.sheet_no}`);
  await expect(page.getByTestId('pr7p')).toBeVisible();
  await expect(page.getByTestId('pr7p-rail-sheet')).toHaveCount(all.length);
  await expect(page.getByTestId('pr7p-rail').locator('[aria-current="page"]')).toContainText(cm.title);
  await expect(page.getByTestId('pr-restool-confirm')).toBeVisible();
  const before = await api(request, 'GET', `/proposals/${id}/sheets/${cm.sheet_id}`);
  const row = page.getByTestId('pr7p-preview').locator('[data-row]').last();
  if (await row.count()) {
    await row.click();
    await expect(page.getByRole('toolbar', { name: '선택한 행' })).toBeVisible();
    const field = page.getByTestId('pr7p-field').nth(1);
    await field.fill('4시간 이내');
    await shot(page, 'flow-pr7p-edit');
    await page.getByTestId('pr7p-apply').click();
    await expect.poll(async () => JSON.stringify((await api(request, 'GET', `/proposals/${id}/sheets/${cm.sheet_id}`)).content), { timeout: 10_000 }).toContain('4시간 이내');
    const after = await api(request, 'GET', `/proposals/${id}/sheets/${cm.sheet_id}`);
    expect(after.rev).toBeGreaterThan(before.rev);
  }
  await expect(page.getByTestId('pr7p-notes')).toBeVisible();
  await shot(page, 'flow-pr7p');
});
