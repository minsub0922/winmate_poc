/**
 * MI 새 흐름(웹앱 ① v58 보드 webapp1 MI0 · MI1 · MI1_Branch · MI2_Loading · MI2 · MI3 · MI_Done · MI_DoneJson) — docs/scenarios/11-content-flow.md §1 · §6.
 * 실제 스택: 게이트웨이 → mi(+워커) · storyboard 허브 · ai-tools(mock 고정 응답 mocks/ai-tools/mi.flow_analyze.v1 · mi.flow_search.v1 = 보드 예시 문장).
 * 화면 폭 · 칸 폭을 숫자로 재고(본문 열 1180 · 보드 고정 칸) e2e/mi/__screens__/<보드>-new.png 를 남긴다.
 * 실행: make e2e-feature SERVICE=mi (또는 WM_E2E_SUITE=mi WM_E2E_DEV=1 WM_E2E_PORT=5203 npx playwright test e2e/mi/mi-flow.spec.ts --workers=1)
 */
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { shot } from './helpers';

test.describe.configure({ mode: 'serial' });

const box = async (page: Page, sel: string) => (await page.locator(sel).first().boundingBox())!;
const near = (got: number, want: number, tol = 0.6) => expect(Math.abs(got - want), `${got} ≈ ${want}`).toBeLessThanOrEqual(tol);

async function hub(request: APIRequestContext, sbId: string) {
  const r = await request.get(`/api/storyboard/v1/flows/${sbId}`);
  expect(r.ok()).toBeTruthy();
  return r.json();
}

/** 정제 줄 하나(요약 문장으로) */
const row = (page: Page, text: string | RegExp) => page.locator('.mif-row').filter({ hasText: text });

let SB = { id: '', name: '' };
let CODE = '';

test('새 MI — 목록 → Gate → 분석 로딩 → 검색어 · 조건 → 정제 → 저장 v1 → 다시 고치기 → v2 · 전체 JSON', async ({ page, request }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  SB = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });

  // ── MI0 목록(보드 List content=mi) → 새 MI
  await page.goto('/mi');
  await expect(page.getByRole('heading', { level: 1, name: 'Market Intelligence' })).toBeVisible();
  await expect(page.getByText('사전 작업 · 최소 DSS까지 된 Storyboard')).toBeVisible();
  await expect(page.getByText('후속 작업 · 없음')).toBeVisible();
  await page.getByRole('link', { name: '새 MI' }).first().click();

  // ── MI1 Gate — 우리 Storyboard 고르기
  await expect(page).toHaveURL(/\/mi\/new$/);
  await expect(page.getByRole('heading', { level: 1, name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새 MI');
  const mine = page.getByRole('radio', { name: new RegExp(SB.name) });
  await mine.click();
  await expect(mine).toHaveAttribute('aria-checked', 'true');
  await expect(page.locator('.fl-gatefoot')).toContainText(`${SB.name}에 MI가 연결돼요`);
  await shot(page, 'MI1-new');
  await page.getByRole('button', { name: /이 Storyboard로 시작/ }).click();

  // ── MI2_Loading — AI 가 Storyboard 를 먼저 읽는다(CF-08 의 MI 예외)
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}$/);
  const mid = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  await expect(page.getByRole('heading', { level: 1, name: 'Storyboard를 읽는 중이에요' })).toBeVisible();
  await expect(page.getByTestId('mif-steps')).toContainText(`Storyboard ${SB.id} 읽기`);
  await expect(page.getByText('AI가 Storyboard를 분석하고 있어요')).toBeVisible();

  // ── MI2 검색어 · 검색 조건
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.mif-basis')).toContainText('AI 분석');
  await expect(page.locator('.mif-basis__chip')).toHaveText(['고객사E 자산운용', '업종오피스 · 업무시설', '공간로비 외 2', '요구에너지 절감 · AI Ready']);
  await expect(page.locator('.mif-col__t')).toHaveText(['시장', '고객사', '사용자']);
  await expect(page.locator('.mif-col__n')).toHaveText(['검색어 4', '검색어 3', '검색어 3']);
  await expect(page.locator('.mif-foot .wm-flow__summary')).toHaveText('검색어 10개 · 1–2분');
  await expect(page.locator('.mif-opt__k')).toHaveText(['기간', '출처']);           // 처음 만들 때는 「기존 MI」 줄이 없다
  const doc0 = await (await request.get(`/api/mi/v1/mi-flows/${mid}`)).json();
  CODE = doc0.code;
  // 조건(정부 통계 더하기)
  await page.getByRole('group', { name: '출처' }).getByRole('button', { name: '정부 통계' }).click();
  await expect(page.getByRole('group', { name: '출처' }).getByRole('button', { name: '정부 통계' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.mif-foot .wm-flow__summary')).toHaveText('검색어 10개 · 1–2분');
  await expect.poll(async () => (await (await request.get(`/api/mi/v1/mi-flows/${mid}`)).json()).filters.sourceTypes).toEqual(['뉴스', '공시 · IR', '리포트', '정부 통계']);
  await page.getByRole('button', { name: '웹 검색 후 정제로' }).click();

  // ── 웹 검색(단계 카드) → MI3 정제
  await expect(page.getByRole('heading', { level: 1, name: '웹에서 찾는 중이에요' })).toBeVisible();
  await expect(page.getByRole('heading', { level: 1, name: '찾은 정보를 정리해요' })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('mif-count')).toHaveText('찾은 13 · 담음 13');
  await expect(page.locator('.mif-tab')).toHaveText(['시장5/5', '고객사4/4', '사용자4/4']);
  await expect(page.locator('.mif-tag')).toHaveCount(0);                               // 처음 만들 때는 v1에서 유지 / 새로 찾음 표시가 없다
  const first = row(page, '프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다.');
  await expect(first.locator('.mif-row__meta')).toHaveText(/^리포트부동산 리서치 · 2026-08$/);
  await expect(row(page, '공실률').locator('.mif-numchk')).toHaveText('수치 원문 확인');
  await expect(row(page, '건물 에너지 효율').locator('.mif-kind')).toHaveText('정부 통계');
  // 원문(요약형 검색 — URL 없음 → 검색 결과 글)
  await first.getByRole('button', { name: '원문' }).click();
  const orig = page.getByRole('dialog', { name: '원문 · 검색 결과' });
  await expect(orig).toContainText('프라임 오피스 스마트 빌딩 도입');
  await expect(orig).toContainText('부동산 리서치 2026-08 리포트에 따르면');
  await orig.getByRole('button', { name: '닫기' }).last().click();
  // 문장 고치기
  await first.getByRole('button', { name: '문장 고치기' }).click();
  await page.getByLabel('고친 문장').fill('프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석');
  await page.getByLabel('고친 문장').press('Enter');
  await expect(row(page, '업계 분석')).toHaveCount(1);
  // 빼기 2개(임대 · 정부 통계) → 담음 11
  await row(page, '공실률').getByRole('checkbox').click();
  await row(page, '건물 에너지 효율').getByRole('checkbox').click();
  await expect(page.getByTestId('mif-count')).toHaveText('찾은 13 · 담음 11');
  await expect(page.locator('.mif-tab').first()).toHaveText('시장3/5');
  await page.locator('.mif-tab', { hasText: '고객사' }).click();
  await expect(page.locator('.mif-row')).toHaveCount(4);
  await expect(row(page, '에너지 사용을').locator('.mif-row__meta')).toContainText('공시 · IR지속가능경영보고서 · 2026-04');
  await page.locator('.mif-tab', { hasText: '시장' }).click();

  // ── 저장 v1 → MI_Done
  await page.getByRole('button', { name: 'MI 저장 · v1' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'MI를 저장했어요' })).toBeVisible();
  await expect(page).toHaveURL(/\?done=1$/);
  await expect(page.locator('.wm-done__head')).toContainText('시장 3 · 고객사 4 · 사용자 4 · 담은 정보 11개를 Storyboard에 담았어요');
  let flow = await hub(request, SB.id);
  expect(flow.stages.mi.ref).toBe(CODE);
  expect(flow.stages.mi.ver).toBe(1);
  expect(flow.stages.mi.counts).toEqual({ found: 13, kept: 11, numberCheck: 2 });
  expect(flow.stages.mi.items).toHaveLength(11);
  expect(flow.stages.mi.items[0].summary).toBe('프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석');
  expect(flow.stages.mi.items[0].source).toEqual({ type: '리포트', name: '부동산 리서치', date: '2026-08', url: null });
  expect(flow.stages.mi.filters.sourceTypes).toContain('정부 통계');
  expect(flow.cells.find((c: { key: string }) => c.key === 'mi').route).toBe(`/mi/flow/${mid}`);
  // 새로 고침해도 완료 화면
  await page.reload();
  await expect(page.getByRole('heading', { level: 1, name: 'MI를 저장했어요' })).toBeVisible();

  // ── 다시 고치기 → Storyboard 다시 읽기(보드 MI2_Loading: 「MI-01 수정」 · 「v1을 고쳐요 · 저장하면 v2」)
  await page.getByRole('button', { name: '다시 고치기' }).click();
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(`${CODE} 수정`);
  await expect(page.locator('.wm-sbbar__note')).toHaveText(`${CODE} v1을 고쳐요 · 저장하면 v2`);
  const steps = page.getByTestId('mif-steps');
  await expect(steps.locator('.mif-step[data-state="run"]')).toHaveText(/고객사 · 업종 · 공간 · 요구 뽑기/, { timeout: 10_000 });
  await expect(steps.locator('.mif-step').first()).toContainText('요구사항 · DSS · 요약본');
  await page.screenshot({ path: 'e2e/mi/__screens__/MI2_Loading-new.png' });
  // 폭: 본문 열 1180 · 단계 카드 = 1180 − 40×2
  near((await box(page, '.mif-screen')).width, 1180);
  near((await box(page, '.mif-steps')).width, 1100);
  near((await box(page, '.mif-step')).height, 45);

  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.mif-opt__k')).toHaveText(['기간', '출처', `기존 ${CODE}`]);
  await expect(page.getByRole('group', { name: `기존 ${CODE}` }).getByRole('button', { name: '담은 정보 11개 유지 · 새로 찾은 것만 더하기' })).toHaveAttribute('aria-pressed', 'true');
  // 보드 MI2 모양: 「건물 에너지 효율 규제」 빼고 · 출처에서 정부 통계 빼고 → 검색어 9개
  await page.getByRole('button', { name: '빼기 · 건물 에너지 효율 규제' }).click();
  await page.getByRole('group', { name: '출처' }).getByRole('button', { name: '정부 통계' }).click();
  await expect(page.locator('.mif-foot .wm-flow__summary')).toHaveText('검색어 9개 · 1–2분');
  await shot(page, 'MI2-new');
  // 폭: 검색어 세 칸 = (1100 − 12×2) / 3 · 높이 300 · 조건 키 96 · 주 버튼 h48 · 왼쪽 여백 40
  const flowBox = await box(page, '.mif-screen');
  const cols = page.locator('.mif-col');
  for (let i = 0; i < 3; i += 1) {
    const b = (await cols.nth(i).boundingBox())!;
    near(b.width, (1100 - 24) / 3);
    near(b.height, 300);
  }
  near((await box(page, '.mif-col')).x - flowBox.x, 40);
  near((await box(page, '.mif-opt__k')).width, 96);
  near((await box(page, '.mif-opts')).width, 1100);
  near((await box(page, '.mif-foot .wm-flow__primary')).height, 48);
  near((await box(page, '.mif-q')).height, 34);
  near((await box(page, '.mif-chip')).height, 30);
  // 검색어 더하기 · 빼기 · 다시 넣기
  await page.getByLabel('사용자 검색어 추가').fill('오피스 라운지 이용 행태');
  await page.getByLabel('사용자 검색어 추가').press('Enter');
  await expect(page.locator('[data-group="user"] .mif-q')).toHaveCount(4);
  await expect(page.locator('[data-group="user"] .mif-col__n')).toHaveText('검색어 4');
  await page.getByRole('button', { name: '빼기 · 오피스 라운지 이용 행태' }).click();
  await expect(page.locator('[data-group="user"] .mif-q--off')).toHaveText('오피스 라운지 이용 행태');
  await page.getByRole('button', { name: '다시 넣기 · 건물 에너지 효율 규제' }).click();
  await page.getByRole('group', { name: '출처' }).getByRole('button', { name: '정부 통계' }).click();
  await expect(page.locator('.mif-foot .wm-flow__summary')).toHaveText('검색어 10개 · 1–2분');
  await page.getByRole('button', { name: '웹 검색 후 정제로' }).click();

  // ── MI3(보드: 찾은 13 · 담음 12 · 시장 4/5 · v1에서 유지 / 새로 찾음)
  await expect(page.getByRole('heading', { level: 1, name: '찾은 정보를 정리해요' })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('mif-count')).toHaveText('찾은 13 · 담음 13');
  await expect(row(page, '업계 분석').locator('.mif-tag')).toHaveText('v1에서 유지');
  await expect(row(page, '공실률').locator('.mif-tag')).toHaveText('새로 찾음');
  await row(page, '건물 에너지 효율').getByRole('checkbox').click();
  await expect(page.getByTestId('mif-count')).toHaveText('찾은 13 · 담음 12');
  await expect(page.locator('.mif-tab')).toHaveText(['시장4/5', '고객사4/4', '사용자4/4']);
  await expect(page.locator('.mif-row .mif-tag')).toHaveText(['v1에서 유지', '새로 찾음', 'v1에서 유지', 'v1에서 유지', '새로 찾음']);   // 찾은 순서(보드 MI3 처럼 섞여 보인다)
  await shot(page, 'MI3-new');
  near((await box(page, '.mif-list')).width, 1100);
  near((await box(page, '.mif-row')).height, 76);
  near((await box(page, '.mif-chk')).width, 22);
  near((await box(page, '.mif-tab')).height, 34);
  near((await box(page, '.mif-ghost30')).height, 30);

  // ── 저장 v2 → MI_Done · MI_DoneJson
  await page.getByRole('button', { name: 'MI 저장 · v2' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'MI를 고쳐 저장했어요' })).toBeVisible();
  await expect(page.locator('.wm-done__head')).toContainText(`${CODE} v1 → v2 · 담은 정보 11 → 12`);
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(CODE);
  await expect(page.getByText(/"stages\.mi": \{/)).toBeVisible();
  await expect(page.locator('.wm-done__md pre')).toContainText('- 시장 4 · 고객사 4 · 사용자 4 (+1)');
  await expect(page.locator('.mif-nofollow')).toContainText('이 콘텐츠는 후속 작업이 없어요.');
  await expect(page.locator('.mif-nofollow').getByRole('link', { name: 'Storyboard로' })).toHaveAttribute('href', `/storyboard/flow/${SB.id}`);
  await shot(page, 'MI_Done-new');
  near((await box(page, '.wm-done__card')).width, 1020);
  flow = await hub(request, SB.id);
  expect(flow.stages.mi.ver).toBe(2);
  expect(flow.stages.mi.prevVer).toBe(1);
  expect(flow.stages.mi.counts).toEqual({ found: 13, kept: 12, numberCheck: 3 });
  expect(flow.stages.mi.items.map((x: { addedIn: string }) => x.addedIn).filter((v: string) => v === 'v2')).toHaveLength(1);
  expect(flow.stages.mi.queries.user).toEqual(['하이브리드 근무 회의실 수요', '오피스 방문객 출입 경험', '임차인 선호 오피스 설비']);   // 뺀 검색어는 안 들어간다
  await page.getByRole('button', { name: '전체 JSON 보기' }).click();
  const json = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(json).toBeVisible();
  await expect(json.locator('.wm-jsonline--add').first()).toContainText('"mi": {');
  await shot(page, 'MI_DoneJson-new');
  await json.getByRole('button', { name: '닫기' }).last().click();

  // ── 목록에 저장된 MI(허브) — 연결된 Storyboard 칩
  await page.goto('/mi');
  const line = page.locator('.fl-tr', { hasText: `${CODE} v2` });
  await expect(line).toHaveCount(1);
  await expect(line.locator('.fl-sbchip')).toHaveText(SB.name);
  await expect(line.getByRole('link', { name: '열기' })).toHaveAttribute('href', `/mi/flow/${mid}`);
  await shot(page, 'MI0-new');
});

test('MI1_Branch — 이미 MI 가 있는 Storyboard → 복제본 만들기 → 분기 Storyboard 에 새 MI', async ({ page, request }) => {
  test.setTimeout(120_000);
  test.skip(!SB.id || !CODE, '앞 테스트가 만든 Storyboard 가 필요해요');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/mi/new?sb=${SB.id}`);
  const mine = page.getByRole('radio', { name: new RegExp(SB.name) }).first();
  await expect(mine).toHaveAttribute('aria-checked', 'true');
  await expect(mine).toContainText(`${CODE} v2 있음`);
  await expect(page.locator('.fl-exist')).toContainText(`이 Storyboard에는 MI ${CODE} v2가 이미 있어요`);
  await page.getByRole('radio', { name: /복제본 만들기/ }).click();
  await expect(page.getByRole('button', { name: /분기 만들고 시작/ })).toBeVisible();
  await expect(page.locator('.fl-gatefoot')).toContainText(`‘${SB.name} · 분기 B’가 새로 생겨요`);
  await shot(page, 'MI1_Branch-new');
  await page.getByRole('button', { name: /분기 만들고 시작/ }).click();
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}$/);
  const bid = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  const d = await (await request.get(`/api/mi/v1/mi-flows/${bid}`)).json();
  expect(d.code).not.toBe(CODE);
  expect(d.sb_id).not.toBe(SB.id);
  const b = await hub(request, d.sb_id);
  expect(b.parent).toBe(SB.id);
  await expect(page.locator('.wm-sbbar__chip')).toContainText(b.name);
  await expect(page.locator('.wm-sbbar__branch')).toHaveText('분기');
  // 원본 MI 는 그대로
  expect((await hub(request, SB.id)).stages.mi.ref).toBe(CODE);
});

test('Storyboard 「만들기」(?sb=&auto=1) → Gate 없이 바로 분석 로딩 · 이전 흐름 링크(?rq=) → /mi/legacy/new', async ({ page, request }) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });
  await page.goto(`/mi/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}$/);
  await expect(page.getByRole('heading', { level: 1, name: 'Storyboard를 읽는 중이에요' })).toBeVisible();
  await expect(page.locator('.wm-sbbar__note')).toHaveText('Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨');
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새 MI');
  await shot(page, 'MI2_Loading-first-new');
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  // DSS 전 Storyboard 는 Gate 에서 고를 수 없다(점선 · DSS 먼저)
  const pre = await makeStoryboard(request, { name: `판교 스타트업 단지 ${tag()}` });
  await page.goto(`/mi/new?sb=${pre.id}&auto=1`);
  const off = page.getByRole('radio', { name: new RegExp(pre.name) });
  await expect(off).toHaveAttribute('aria-disabled', 'true');
  await expect(off).toContainText('DSS 먼저');
  await expect(page).toHaveURL(/\/mi\/new\?/);
  // 요구사항 정의서의 「Market Intelligence」(이전 흐름) 링크
  await page.goto('/mi/new?rq=rq_TEST');
  await expect(page).toHaveURL(/\/mi\/legacy\/new\?rq=rq_TEST$/);
});
