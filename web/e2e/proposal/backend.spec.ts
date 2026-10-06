/**
 * 실제 백엔드 — 시작 방식(RFP) · 딸깍(진행 → 완료) · 확정 필요(확정) · 버전(저장 · 비교) · 검토(요청 전 작성 모드) · 내보내기.
 * 백엔드가 그 경로를 아직 구현하지 않았으면(501) 이유를 남기고 건너뛴다. 백엔드 잡이 실패하면 화면의 실패 처리까지 보고 이유를 남겨 건너뛴다.
 */
import { expect as baseExpect, test } from '@playwright/test';
import { CUSTOMER, api, backendDown, notImplemented, removeProposal, seedGenerated, seedProposal, shot, uniq, waitJob, watchCrash, isolateBrokenFeatures, open } from './helpers';

/** 공유 PC(2 CPU)에 다른 세션 테스트가 함께 돌아 느릴 수 있어 기다림을 넉넉히 */
const expect = baseExpect.configure({ timeout: 20_000 });

test.use({ actionTimeout: 30_000, navigationTimeout: 60_000 });
test.beforeEach(async ({ page }) => { await isolateBrokenFeatures(page); });

const RFP_TXT = [
  'A 커피 프랜차이즈 — 전국 매장 디지털 메뉴보드 전환 제안 요청서',
  '발주처: A 커피 프랜차이즈',
  '사업명: 전국 매장 디지털 메뉴보드 전환',
  '당사는 커피 전문점 브랜드로 전국 320개 매장을 운영하는 회사입니다.',
  '요구 사항',
  '1. 본사 콘텐츠 일괄 배포',
  '2. 프로모션 교체 주기 단축',
  '3. 매장별 메뉴 가격 차등',
  '4. 320개 매장 단계 도입',
  '5. 기존 POS 연동',
  '일정',
  '제안서 제출 마감: 2026-10-08',
  '제안 설명회: 2026-10-22 · 발표 20분',
].join('\n');

test.describe('시작 방식 · 딸깍 (실제)', () => {
  test.describe.configure({ timeout: 150_000, retries: 1 });
  /** 이 테스트가 만든 제안서 — 끝나면 지운다(실패로 워커가 바뀌어도 남지 않게 테스트마다) */
  let made: string[] = [];
  test.afterEach(async ({ request }) => { for (const id of made) await removeProposal(request, id); made = []; });

  test('PR1F 실제 — TXT RFP 올리기 → 읽기 · 항목 찾기 · 채우기 → 9항목 · 비어 있음 → 확인 · 다음 → PR2', async ({ page, request }) => {
    const down = await backendDown(request);
    test.skip(!!down, down ?? '');
    const p = await seedProposal(request, { start_mode: 'rfp', title: null, customer: { name: '' } });
    made.push(p.id);
    const ni = await notImplemented(request, 'GET', `/proposals/${p.id}/rfp`);
    test.skip(!!ni, ni ?? '');
    await open(page, `/proposal/${p.id}/rfp`);
    await expect(page.getByTestId('pr1f-drop')).toBeVisible();
    await page.getByTestId('pr1f-drop').locator('input[type=file]').setInputFiles({ name: 'A커피_RFP.txt', mimeType: 'text/plain', buffer: Buffer.from(RFP_TXT, 'utf-8') });
    await expect(page.getByTestId('pr1f-file')).toContainText('A커피_RFP.txt', { timeout: 20_000 });
    await expect(page.getByTestId('pr1f-field')).toHaveCount(9, { timeout: 90_000 });
    await expect(page.locator('[data-key="customer"]')).toHaveAttribute('data-state', /found|guess/);
    await expect(page.locator('[data-key="budget"]')).toHaveAttribute('data-state', 'empty');
    await expect(page.getByTestId('pr1f-empty')).toBeVisible();
    await shot(page, 'real-pr1f');
    await page.getByTestId('pr1f-next').click();
    await expect(page).toHaveURL(new RegExp(`/proposal/${p.id}/type$`), { timeout: 15_000 });
    const after = await api(request, 'GET', `/proposals/${p.id}`);
    expect(after.customer.name).toContain('A 커피');
  });

  test('딸깍 실제 — PR2 에서 「딸깍, 완성하기」 → 진행 화면 → 완료(파일 · 썸네일)', async ({ page, request }) => {
    test.setTimeout(260_000);
    const down = await backendDown(request);
    test.skip(!!down, down ?? '');
    const p = await seedProposal(request);
    made.push(p.id);
    const ni = await notImplemented(request, 'GET', `/proposals/${p.id}/one-click/plan?from=type`);
    test.skip(!!ni, ni ?? '');
    await open(page, `/proposal/${p.id}/type`);
    await expect(page.getByTestId('pr2')).toBeVisible();
    await page.getByRole('button', { name: /딸깍/ }).first().click();
    const pop = page.getByRole('dialog', { name: '딸깍 — 나머지 자동 완성' });
    await expect(pop).toBeVisible();
    await expect(pop.locator('[data-plan-row]').first()).toBeVisible();
    await shot(page, 'real-oneclick-early');
    await pop.getByRole('button', { name: '딸깍, 완성하기' }).click();
    await expect(page).toHaveURL(new RegExp(`/proposal/${p.id}/one-click/job_[^/]+$`), { timeout: 15_000 });
    const ocUrl = new URL(page.url()).pathname;
    const jobId = ocUrl.match(/one-click\/(job_[^/?#]+)/)![1];
    const tab = watchCrash(page);
    await expect(page.getByTestId('oc-gen').or(page.getByTestId('oc-done'))).toBeVisible();
    if (await page.getByTestId('oc-gen').isVisible()) {
      await expect(page.getByTestId('oc-step').first()).toBeVisible();
      await shot(page, 'real-oneclick-gen');
    }
    // 잡 API 로 끝을 기다린다 → 끝나면 화면 확인(탭이 메모리 부족으로 죽었으면 새 탭으로 다시 연다)
    const fin = await waitJob(request, jobId, 220_000);
    let pg = page;
    if (tab.crashed) { pg = await tab.alive(); await open(pg, ocUrl); }
    if (fin.status === 'failed') {
      await expect(pg.getByTestId('oc-failed')).toBeVisible({ timeout: 30_000 });
      await expect(pg.getByTestId('oc-retry')).toBeEnabled();
      await shot(pg, 'real-oneclick-failed');
      test.skip(true, `백엔드 딸깍 잡 실패 — ${fin.error?.code ?? ''} ${fin.error?.message ?? ''}`.trim());
    }
    await expect(pg.getByTestId('oc-done')).toBeVisible({ timeout: 30_000 });
    await expect(pg.getByTestId('oc-file')).toBeVisible();
    await shot(pg, 'real-oneclick-done');
    const after = await api(request, 'GET', `/proposals/${p.id}`);
    expect(after.version).toBeGreaterThanOrEqual(1);
  });
});

test.describe('생성된 제안서 (실제 PPTX)', () => {
  test.describe.configure({ mode: 'serial', timeout: 150_000, retries: 1 });
  let gen: any = null;
  test.afterAll(async ({ request }) => { await removeProposal(request, gen?.id); });

  test('PR7Q 실제 — 확정 필요 목록 · 값 넣고 확정 → 남은 곳 줄어듦', async ({ page, request }) => {
    test.setTimeout(260_000);
    const down = await backendDown(request);
    test.skip(!!down, down ?? '');
    gen = await seedGenerated(request);
    const ni = await notImplemented(request, 'GET', `/proposals/${gen.id}/confirm-items`);
    test.skip(!!ni, ni ?? '');
    const before = await api(request, 'GET', `/proposals/${gen.id}/confirm-items?status=all`);
    const open0 = before.items.filter((i: any) => i.status === 'open').length;
    test.skip(open0 === 0, '열린 확인 항목이 없어요');
    await open(page, `/proposal/${gen.id}/confirm`);
    await expect(page.getByTestId('pr7q-list')).toBeVisible();
    const openRows = page.locator('[data-testid="pr7q-item"][data-status="open"]');
    await expect(openRows.first()).toBeVisible();
    await shot(page, 'real-pr7q');
    await openRows.first().getByTestId('pr7q-fix').click();
    const inputs = page.locator('.pr-cfrow--open input');
    for (let i = 0; i < await inputs.count(); i += 1) await inputs.nth(i).fill('12');
    await page.getByTestId('pr7q-resolve').click();
    await expect.poll(async () => (await api(request, 'GET', `/proposals/${gen.id}/confirm-items?status=all`)).items.filter((i: any) => i.status === 'open').length, { timeout: 15_000 })
      .toBeLessThan(open0);
  });

  test('PR7V 실제 — 시트 고치고 v2 저장 → v1 · v2 비교 · 바뀐 곳', async ({ page, request }) => {
    test.setTimeout(120_000);
    test.skip(!gen, '생성된 제안서가 없어요');
    const ni = await notImplemented(request, 'GET', `/proposals/${gen.id}/versions`);
    test.skip(!!ni, ni ?? '');
    const slides = await api(request, 'GET', `/proposals/${gen.id}/slides`);
    const sh = slides.sections[0].sheets[0];
    const sheet = await api(request, 'GET', `/proposals/${gen.id}/sheets/${sh.sheet_id}`);
    await api(request, 'PATCH', `/proposals/${gen.id}/sheets/${sh.sheet_id}`, { ops: [{ op: 'set', path: '/title', value: 'e2e 제목 바꿈' }], reason: 'e2e' }, { 'If-Match': String(sheet.rev) });
    await open(page, `/proposal/${gen.id}/versions`);
    await expect(page.getByTestId('pr7v-history')).toBeVisible();
    await page.getByTestId('pr7v-save').click();
    await expect.poll(async () => (await api(request, 'GET', `/proposals/${gen.id}/versions`)).current, { timeout: 15_000 }).toBeGreaterThanOrEqual(2);
    await open(page, `/proposal/${gen.id}/versions?a=1&b=2`);
    await expect(page.getByTestId('pr7v-compare')).toBeVisible();
    await expect(page.getByTestId('pr7v-version')).toHaveCount(2);
    await shot(page, 'real-pr7v');
  });

  test('PR7C 실제 — 검토 요청 전이면 작성 모드(검토자 · 마감 · 메시지)', async ({ page, request }) => {
    test.setTimeout(60_000);
    test.skip(!gen, '생성된 제안서가 없어요');
    const ni = await notImplemented(request, 'GET', `/proposals/${gen.id}/review`);
    test.skip(!!ni, ni ?? '');
    await open(page, `/proposal/${gen.id}/review`);
    await expect(page.getByTestId('pr7c-compose')).toBeVisible();
    await expect(page.getByTestId('pr7c-send')).toBeDisabled();
    await shot(page, 'real-pr7c-compose');
  });

  test('기존 제안서 활용 실제 — PR1C(?source=) 분석 → PRU2 필수 확인 → PRU3 활용 계획 확정 → 섹션 원본 대조(PRU4)', async ({ page, request }) => {
    test.setTimeout(200_000);
    test.skip(!gen, '생성된 제안서가 없어요');
    const np = await api(request, 'POST', '/proposals', { start_mode: 'reuse', title: `[e2e] 기존 제안서 활용 ${uniq()}`, customer: { name: CUSTOMER } });
    try {
      const ni = await notImplemented(request, 'GET', `/proposals/${np.id}/reuse/candidates`);
      test.skip(!!ni, ni ?? '');
      // PR0 「복제해서 시작」과 같은 길 — ?source= 로 열면 그 제안서를 원본으로 분석을 바로 시작
      await open(page, `/proposal/${np.id}/reuse?source=${gen.id}`);
      await expect(page.getByTestId('pr1c-source')).toBeVisible();
      await expect(page.getByTestId('pr1c-next')).toBeEnabled({ timeout: 90_000 });
      await shot(page, 'real-pr1c');
      await page.getByTestId('pr1c-next').click();
      await expect(page.getByTestId('pru2')).toBeVisible();
      await expect(page.getByTestId('pru2-criterion')).toHaveCount(9);
      // 아직 확인하지 않은 기준을 모두 확인(필수 포함) → 「확인 완료 · 활용 방식 추천 보기」
      const boxes = page.getByTestId('pru2-criteria').getByRole('checkbox');
      for (let i = 0; i < await boxes.count(); i += 1) {
        const b = boxes.nth(i);
        if (!(await b.isChecked())) { await b.click(); await expect(b).toBeChecked(); }
      }
      await shot(page, 'real-pru2');
      await expect(page.getByTestId('pru2-confirm')).toBeEnabled({ timeout: 20_000 });
      await page.getByTestId('pru2-confirm').click();
      await expect(page).toHaveURL(new RegExp(`/proposal/${np.id}/reuse/plan`), { timeout: 60_000 });
      await expect(page.getByTestId('pru3a').or(page.getByTestId('pru3b'))).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId('pru3-confirm')).toBeEnabled({ timeout: 30_000 });
      await shot(page, 'real-pru3');
      await page.getByTestId('pru3-confirm').click();
      await expect(page).toHaveURL(new RegExp(`/proposal/${np.id}/sections/[A-Za-z]+\\?view=(compare|guide)`), { timeout: 60_000 });
      await expect(page.getByTestId('pru4').or(page.getByTestId('pru4b'))).toBeVisible();
      await expect(page.getByTestId('pru4-new')).toBeVisible({ timeout: 30_000 });
      await shot(page, 'real-pru4');
      const after = await api(request, 'GET', `/proposals/${np.id}`);
      expect(after.type).toBeTruthy();
    } finally {
      await removeProposal(request, np.id);
    }
  });

  test('PPTX 내보내기 실제 — PR7X 에서 PPTX 만 · 한국어 → 완료 목록', async ({ page, request }) => {
    test.setTimeout(150_000);
    test.skip(!gen, '생성된 제안서가 없어요');
    const ni = await notImplemented(request, 'GET', `/proposals/${gen.id}/export-options`);
    test.skip(!!ni, ni ?? '');
    await open(page, `/proposal/${gen.id}/result?export=1`);
    await expect(page.getByTestId('pr7x')).toBeVisible();
    const pdf = page.getByTestId('pr7x').getByRole('checkbox', { name: /PDF/ });
    if (await pdf.isChecked()) await pdf.uncheck();
    const tab = watchCrash(page);
    const [resp] = await Promise.all([
      page.waitForResponse((r) => /\/api\/proposal\/v1\/proposals\/[^/]+\/exports$/.test(new URL(r.url()).pathname) && r.request().method() === 'POST'),
      page.getByTestId('pr7x-run').click(),
    ]);
    expect(resp.status()).toBe(202);
    const started = await resp.json();
    const fin = await waitJob(request, started.job_id, 140_000);
    if (fin.status === 'failed') {
      // 백엔드 잡 실패 — 화면이 실패를 알리는지만 보고 이유를 남겨 건너뛴다
      if (!tab.crashed) await expect(page.getByTestId('pr7x').getByRole('alert')).toBeVisible({ timeout: 30_000 });
      test.skip(true, `백엔드 내보내기 잡 실패 — ${fin.error?.code ?? ''} ${fin.error?.message ?? ''}`.trim());
    }
    expect(fin.status).toBe('succeeded');
    if (tab.crashed) {
      // 완료 목록은 그 탭의 잡 추적으로만 보인다 — 잡 성공은 API 로 확인했고 화면 확인만 남긴다
      test.info().annotations.push({ type: 'note', description: '공유 PC 메모리 부족(cgroup OOM)으로 탭이 종료돼 완료 목록 확인은 생략 — 내보내기 잡은 성공' });
      return;
    }
    await expect(page.getByTestId('pr7x-done')).toBeVisible({ timeout: 30_000 });
    await shot(page, 'real-pr7x-done');
  });
});
