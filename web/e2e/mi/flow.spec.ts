/**
 * MI 기본 흐름(실제 mi · 플랫폼 · mock 모델) — MI0 → MI1 → MI2A → MI3G → MI3 → MI3S → MI3V → MI3P → MI3L → MI4.
 * AC-MI-86(입력 없음 → 비활성 · 고객사만 → 활성 · 800ms 뒤 draft 생성) · AC-MI-19(진행 → 결과) 화면 쪽.
 */
import { expect, test } from '@playwright/test';
import { CUSTOMER, MI_ID, REQ, api, backendDown, shot, uniq, waitStatus } from './helpers';

test.describe.configure({ mode: 'serial' });

test('MI1 → MI2A → MI3G → MI3 — 새 분석 한 바퀴', async ({ page, request }) => {
  test.setTimeout(240_000);
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');

  await page.goto('/mi');
  await expect(page.getByRole('heading', { name: 'Market Intelligence 작업' })).toBeVisible();
  await expect(page.getByTestId('mi0-header')).toContainText('분석 ');
  await expect(page.getByRole('tablist', { name: '상태 필터' }).getByRole('tab')).toHaveText([/전체/, /진행 중/, /완료/, /업데이트 필요/, /작성 중/]);
  await shot(page, 'mi0-list');

  // 사이드바에도 `새 분석` 같은 제목의 작업이 있을 수 있어(공유 데이터) 머리 버튼(`/mi/new`)을 누른다
  await page.locator('a[href="/mi/new"]').first().click();
  await expect(page).toHaveURL(/\/mi\/new$/);
  const next = page.getByTestId('mi1-next');
  await expect(next).toBeDisabled();
  await expect(next).toHaveAttribute('title', '고객사 · 요구사항 · 파일 중 하나를 입력해 주세요');
  await expect(page.getByText('어떤 고객 요구사항을 기준으로 시장을 분석할까요?', { exact: false })).toBeVisible();
  await shot(page, 'mi1-empty');

  const customer = `${CUSTOMER} ${uniq()}`;
  await page.getByLabel('고객사').fill(customer);
  await expect(next).toBeEnabled();
  await expect(page).toHaveURL(new RegExp(`/mi/${MI_ID.source}/input$`), { timeout: 5_000 });
  const id = page.url().match(MI_ID)![0];
  const draft = await api(request, 'GET', `/analyses/${id}`);
  expect(draft.status).toBe('draft');
  expect(draft.customer_name).toBe(customer);

  await page.getByLabel('요구사항 입력').fill(REQ);
  await shot(page, 'mi1-input');
  await next.click();

  await expect(page).toHaveURL(new RegExp(`/mi/${id}/design$`));
  await expect(page.getByTestId('mi2a-design')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText('에이전트가 정한 분석 설계')).toBeVisible();
  for (const k of ['segment', 'usage', 'scope', 'competitors', 'naming', 'internal', 'depth']) await expect(page.getByTestId(`mi2a-row-${k}`)).toBeVisible();
  await expect(page.getByTestId('mi2a-row-segment')).toContainText('외식 · 카페 (FB)');
  await expect(page.getByTestId('mi-sheets-preview')).toContainText('MI-FB-A');
  await expect(page.getByTestId('mi-dock-title')).toHaveText('분석 설계 · 2 / 3 · 바꿀 것만 고르세요');
  await shot(page, 'mi2a-design');

  // 판단 규칙(MIR 시트)
  await page.getByRole('button', { name: '판단 규칙' }).click();
  await expect(page.getByRole('dialog', { name: '에이전트 라우팅 규칙' })).toBeVisible();
  await expect(page.getByText('에이전트가 스스로 정하는 것, 사람에게 묻는 것')).toBeVisible();
  await expect(page.getByText('사람에게 묻는 경우는 이 넷뿐')).toBeVisible();
  await shot(page, 'mir-rules');
  await page.getByRole('button', { name: '닫기' }).click();

  await page.getByTestId('mi2a-run').click();
  await expect(page).toHaveURL(new RegExp(`/mi/${id}/run$`));
  await expect(page.getByText('분석하고 있어요. 공개 자료와 사내 사례 DB를 찾아 읽고', { exact: false })).toBeVisible();
  await expect(page.getByTestId('mi3g-card').or(page.getByTestId('mi3-card'))).toBeVisible({ timeout: 30_000 });
  if (page.url().endsWith('/run')) await shot(page, 'mi3g-run');

  await expect(page).toHaveURL(new RegExp(`/mi/${id}/result`), { timeout: 150_000 });
  await expect(page.getByTestId('mi3-agent')).toHaveText('분석이 끝났습니다. 4개 영역의 결과를 탭으로 정리했고, 각 항목은 출처와 함께 제안서에 인용할 수 있습니다.');
  await expect(page.getByRole('tab', { name: '시장조사' })).toBeVisible();
  await expect(page.getByTestId('mi-dock-title')).toHaveText('분석 결과 · 3 / 3 · 완료');
  await shot(page, 'mi3-result-market');

  await page.getByRole('tab', { name: '경쟁사 → 삼성 강점' }).click();
  const table = page.getByRole('table', { name: '경쟁사 비교표' });
  await expect(table).toBeVisible();
  await expect(table.getByRole('columnheader')).toHaveText([/요구사항 항목/, /경쟁사 A/, /경쟁사 B/, /경쟁사 C/, /삼성/]);
  await expect(page.getByText(/도출된 삼성 강점 \d/)).toBeVisible();
  await expect(page.getByTestId('mi3-footer')).toContainText('출처 ');
  await shot(page, 'mi3-result-competitor');
});

test('MI3S 출처 패널 · MI3V 수치 확정 · MI3P · MI3L · MI4', async ({ page, request }) => {
  test.setTimeout(240_000);
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
  const { seedDone } = await import('./helpers');
  const a = await seedDone(request);

  await page.goto(`/mi/${a.id}/result?tab=market&panel=sources`);
  const panel = page.getByRole('complementary', { name: '출처 · 근거' });
  await expect(panel).toBeVisible();
  await expect(panel.getByRole('tablist', { name: '출처 종류' }).getByRole('tab')).toHaveText([/^전체\d+$/, /^공개 자료\d+$/, /^사내 사례 DB\d+$/, /^확인 필요\d+$/]);
  await expect(panel.getByTestId('mi3s-selected')).toBeVisible();
  await expect(panel.getByTestId('mi3s-card').first()).toBeVisible();
  await expect(page.getByTestId('mi3s-tab-summary')).toContainText('이 탭 출처');
  await expect(page.getByTestId('mi-dock-title')).toContainText('근거 확인 · 확인 필요');
  await shot(page, 'mi3s-sources');

  // 웹 검색 요약 카드: `원문 열기` 없음 · `URL 붙여 확인` 있음(AC-MI-89, 이 개발 환경 ai-tools mock 은 요약형)
  const summaryCard = panel.locator('[data-kind="websearch_summary"]').first();
  if (await summaryCard.count()) {
    await expect(summaryCard.getByRole('button', { name: '원문 열기' })).toHaveCount(0);
    await expect(summaryCard.getByRole('button', { name: 'URL 붙여 확인' })).toBeVisible();
  }
  await panel.getByRole('button', { name: '패널 닫기' }).click();
  await expect(page).not.toHaveURL(/panel=sources/);

  await page.goto(`/mi/${a.id}/verify`);
  await expect(page.getByTestId('mi3v-card')).toBeVisible();
  await expect(page.getByText(/제안서에 넣기 전에 확정이 필요한 값이 \d+건 있습니다/)).toBeVisible();
  await expect(page.getByRole('tablist', { name: '보기' }).getByRole('tab')).toHaveText([/전체 \d+/, /남은 것 \d+/, /확정 \d+/]);
  const row = page.getByTestId('mi3v-row').filter({ has: page.locator('input[aria-label$="확정 값"]') }).first();
  const input = row.locator('input[aria-label$="확정 값"]');
  const ph = await input.getAttribute('placeholder');
  await input.fill(ph?.includes(':') ? '6 : 4' : '42');
  await input.press('Enter');
  await expect(row).toHaveAttribute('data-status', 'ok', { timeout: 10_000 });
  await shot(page, 'mi3v-verify');
  await page.getByTestId('mi3v-apply').click();
  await expect(page).toHaveURL(new RegExp(`/mi/${a.id}/result`));
  const after = await api(request, 'GET', `/analyses/${a.id}`);
  expect(after.version).toBeGreaterThanOrEqual(2);

  // 연결된 제안서가 없으면 MI3 큰 버튼은 MI4 로(AC-MI-65 뒷부분)
  await expect(page.getByTestId('mi3-send')).toBeEnabled();
  await page.getByTestId('mi3-send').click();
  await expect(page).toHaveURL(new RegExp(`/mi/${a.id}/export$`));

  await page.goto(`/mi/${a.id}/slides`);
  await expect(page.getByTestId('mi3p-card')).toBeVisible();
  await expect(page.getByTestId('mi3p-row').first()).toBeVisible();
  await expect(page.getByText('고르는 순서')).toBeVisible();
  await shot(page, 'mi3p-slides');
  await page.getByRole('button', { name: '레이아웃 바꾸기' }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/${a.id}/slides/sht_`));
  await expect(page.getByTestId('mi3l-templates')).toBeVisible();
  await expect(page.getByRole('radiogroup', { name: '진행 방법' }).getByRole('radio').first()).toBeVisible();
  expect(await page.getByRole('radiogroup', { name: '진행 방법' }).getByRole('radio').count()).toBeGreaterThanOrEqual(2);
  await shot(page, 'mi3l-layout');
  await page.getByRole('link', { name: '취소' }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/${a.id}/slides$`));

  await page.goto(`/mi/${a.id}/export`);
  await expect(page.getByTestId('mi4-card')).toBeVisible();
  await expect(page.getByText('분석 결과를 어디에 쓸지 골라주세요.', { exact: false })).toBeVisible();
  await expect(page.getByTestId('mi4-map').first()).toBeVisible();
  await expect(page.getByTestId('mi4-send')).toBeDisabled();
  await expect(page.getByTestId('mi4-send')).toHaveAttribute('title', '보낼 제안서를 골라 주세요');
  await shot(page, 'mi4-export');

  // Storyboard · Key Message에 근거로 붙이기 — 웹이 근거 스냅숏을 storyboard 계약으로 올린다(02-storyboard §8.3 · storyboard 는 흉내)
  const posted: any[] = [];
  await page.route((u) => u.pathname === '/api/workspace/v1/items' && u.searchParams.get('feature') === 'SB', (r) => r.fulfill({ json: { items: [
    { item_id: 'sb_01M4E2EMISTORYBOARD000001', feature: 'SB', title: 'A 커피 메뉴보드 기획', status: 'draft', route: '/storyboard/sb_01M4E2EMISTORYBOARD000001',
      owner: 'u', owner_name: '최민섭', created_at: '2026-10-06T00:00:00Z', updated_at: '2026-10-06T00:00:00Z' }], next_cursor: null } }));
  await page.route('**/api/storyboard/v1/storyboards/sb_01M4E2EMISTORYBOARD000001/key-messages', (r) => r.fulfill({ json: { items: [
    { id: 'kmsg_1', place_label: 'Part 1', axis_label: '운영 효율', text: '320개 매장을 본사에서 한 번에 바꿉니다', flags: [], evidence: [], kb_refs: [] },
    { id: 'kmsg_2', place_label: 'Part 2', axis_label: '비용', text: '전기료와 인건비를 함께 줄입니다', flags: [], evidence: [], kb_refs: [] }] } }));
  await page.route('**/api/storyboard/v1/storyboards/*/key-messages/*/evidence', async (r) => {
    posted.push({ url: r.request().url(), body: r.request().postDataJSON() });
    await r.fulfill({ status: 201, json: { id: 'kmsg_2', place_label: 'Part 2', text: '전기료와 인건비를 함께 줄입니다', flags: [], evidence: [], kb_refs: [] } });
  });
  await page.getByTestId('mi4-next-storyboard').click();
  const sheet = page.getByRole('dialog', { name: 'Key Message에 근거로 붙이기' });
  await expect(sheet).toBeVisible();
  await expect(sheet.getByLabel('Storyboard')).toHaveValue('sb_01M4E2EMISTORYBOARD000001');
  const kms = sheet.getByRole('radiogroup', { name: 'Key Message' }).getByRole('radio');
  await expect(kms).toHaveCount(2);
  await expect(kms.first()).toHaveAttribute('aria-checked', 'true');
  await kms.nth(1).click();
  const boxes = sheet.locator('.mi-ev__item input[type="checkbox"]');
  await expect(boxes.first()).toBeChecked();
  const strengths = await sheet.locator('.mi-ev__item[data-kind="strength"]').count();
  expect(strengths).toBeGreaterThanOrEqual(1);
  await expect(sheet.getByTestId('mi4-ev-attach')).toHaveText(`근거 ${strengths}건 붙이기`);
  await shot(page, 'mi4-evidence');
  await sheet.getByTestId('mi4-ev-attach').click();
  await expect(sheet.getByTestId('mi4-ev-done')).toContainText(`Part 2 Key Message에 근거 ${strengths}건을 붙였어요.`);
  expect(posted).toHaveLength(strengths);
  expect(posted[0].url).toContain('/key-messages/kmsg_2/evidence');
  expect(posted[0].body.source).toEqual({ service: 'mi', ref_id: a.id, title: expect.any(String), route: `/mi/${a.id}/result` });
  expect(posted[0].body.text.length).toBeGreaterThan(0);
  expect(JSON.stringify(posted)).not.toMatch(/가나 디스플레이|다라 사이니지|마바 미디어/);
  await expect(sheet.getByRole('link', { name: 'Storyboard 에서 보기' })).toHaveAttribute('href', '/storyboard/sb_01M4E2EMISTORYBOARD000001/direction');
  await page.unrouteAll({ behavior: 'ignoreErrors' });
});
