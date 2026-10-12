/**
 * MI 새 흐름(보드 webapp1 v62 — MI0 · 최종본 View content=mi(MI_View · MI_Draft) + 단계 팝업 MI1 · MI1_Branch · MI2_Loading · MI2 · MI3) — docs/scenarios/11-content-flow.md §1 · §6.
 * 실제 스택: 게이트웨이 → mi(+워커) · storyboard 허브 · ai-tools(mock 고정 응답 mocks/ai-tools/mi.flow_analyze.v1 · mi.flow_search.v1 = 보드 예시 문장).
 * 상세에는 페이지 이동이 없다(같은 주소 · `?step=`). 팝업은 1440×900 에서 (130, 50) 1180×800 — 칸 좌표는 팝업 기준(예전 page 좌표에서 x −130 · y −50).
 * 화면 폭 · 칸 폭을 숫자로 재고 e2e/mi/__screens__/<보드>-new.png 를 남긴다.
 * 실행: make e2e-feature SERVICE=mi (또는 WM_E2E_SUITE=mi WM_E2E_DEV=1 WM_E2E_PORT=5203 npx playwright test e2e/mi/mi-flow.spec.ts --workers=1)
 */
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { shot } from './helpers';

test.describe.configure({ mode: 'serial' });

const box = async (page: Page, sel: string) => (await page.locator(sel).first().boundingBox())!;
const lbox = async (l: Locator) => { const b = (await l.boundingBox())!; return { w: Math.round(b.width * 10) / 10, h: Math.round(b.height * 10) / 10, x: Math.round(b.x), y: Math.round(b.y) }; };
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
let MID = '';

test('새 MI — 목록 → ① Gate 팝업 → ② 분석 로딩 · 검색어 · 조건 → ③ 정제 → 저장 v1(최종본) → 단계 칩 고치기 → v2', async ({ page, request }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  SB = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });

  // ── MI0 목록(보드 List content=mi) → 새 MI
  await page.goto('/mi');
  await expect(page.getByRole('heading', { level: 1, name: 'Market Intelligence' })).toBeVisible();
  await expect(page.getByText('사전 작업 · 최소 DSS까지 된 Storyboard')).toBeVisible();
  await expect(page.getByText('후속 작업 · 없음')).toBeVisible();
  await page.getByRole('link', { name: '새 MI' }).first().click();

  // ── MI1 — 빈 최종본(새로 만들기 · 칸마다 자리표시) 위 ① Storyboard 팝업
  await expect(page).toHaveURL(/\/mi\/new$/);
  const gateDlg = page.getByRole('dialog', { name: '새 MI · Storyboard' });
  await expect(gateDlg).toBeVisible();
  expect(await lbox(gateDlg)).toMatchObject({ x: 130, y: 50, w: 1180, h: 800 });
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새로 만들기');
  await expect(page.locator('.fl-detail .fl-dver')).toHaveText('새로 만들기');
  await expect(page.locator('.fl-detail .fl-slot')).toHaveCount(2);
  await expect(gateDlg.locator('.fl-shead__pos')).toHaveText('단계 1/3');
  await expect(gateDlg.locator('.fl-shead__note')).toHaveText('Storyboard를 고르면 MI가 그 Storyboard에 연결돼요 · 고르기 전에 닫으면 목록으로');
  await expect(page.getByRole('heading', { level: 1, name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  await expect(gateDlg.getByRole('link', { name: '목록' })).toHaveCount(0);
  const mine = page.getByRole('radio', { name: new RegExp(SB.name) });
  await mine.click();
  await expect(mine).toHaveAttribute('aria-checked', 'true');
  await expect(page.locator('.fl-gatefoot')).toContainText(`${SB.name}에 MI가 연결돼요`);
  await page.mouse.move(10, 890);
  await shot(page, 'MI1-new');
  await page.getByRole('button', { name: /이 Storyboard로 시작/ }).click();

  // ── MI2_Loading — ② 검색 팝업 안에서 AI 가 Storyboard 를 먼저 읽는다(CF-08 의 MI 예외) · 주소는 ?step=search
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}\?step=search$/);
  MID = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  const stepDlg = page.locator('.fl-stepdlg');
  await expect(page.getByRole('heading', { level: 1, name: 'Storyboard를 읽는 중이에요' })).toBeVisible();
  await expect(page.getByTestId('mif-steps')).toContainText(`Storyboard ${SB.id} 읽기`);
  await expect(page.getByText('AI가 Storyboard를 분석하고 있어요')).toBeVisible();
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText('새로 만들기');
  await expect(stepDlg.locator('.fl-shead__note')).toHaveText('MI를 저장하면 이 Storyboard에 연결돼요');
  await expect(stepDlg.locator('.fl-shead__sb')).toContainText(SB.name);
  await expect(stepDlg.locator('.fl-shead__pos')).toHaveText('단계 2/3');
  await expect(stepDlg.locator('.wm-sbbar')).toHaveCount(0);
  await expect(stepDlg.locator('.wm-flow__back')).toHaveCount(0);                    // 팝업 안 ② 에는 뒤로 링크가 없다

  // ── MI2 검색어 · 검색 조건
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  await expect(page).toHaveURL(/\?step=search$/);
  const doc0 = await (await request.get(`/api/mi/v1/mi-flows/${MID}`)).json();
  CODE = doc0.code;
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(doc0.title);              // 작성 중 = 이름
  await expect(page.locator('.mif-basis')).toContainText('AI 분석');
  await expect(page.locator('.mif-basis__chip')).toHaveText(['고객사E 자산운용', '업종오피스 · 업무시설', '공간로비 외 2', '요구에너지 절감 · AI Ready']);
  await expect(page.locator('.mif-col__t')).toHaveText(['시장', '고객사', '사용자']);
  await expect(page.locator('.mif-col__n')).toHaveText(['검색어 4', '검색어 3', '검색어 3']);
  await expect(page.locator('.mif-foot .wm-flow__summary')).toHaveText('검색어 10개 · 1–2분');
  await expect(page.locator('.mif-opt__k')).toHaveText(['기간', '출처']);           // 처음 만들 때는 「기존 MI」 줄이 없다
  // 조건(정부 통계 더하기)
  await page.getByRole('group', { name: '출처' }).getByRole('button', { name: '정부 통계' }).click();
  await expect(page.getByRole('group', { name: '출처' }).getByRole('button', { name: '정부 통계' })).toHaveAttribute('aria-pressed', 'true');
  await expect.poll(async () => (await (await request.get(`/api/mi/v1/mi-flows/${MID}`)).json()).filters.sourceTypes).toEqual(['뉴스', '공시 · IR', '리포트', '정부 통계']);
  // 팝업 기준 칸(보드 MI2: 본문 1180 · 왼쪽 여백 40 → x 170 · 칸 (1100 − 24) / 3 · h300 · 주 버튼 h48 y780)
  near((await box(page, '.mif-screen')).width, 1180);
  near((await box(page, '.mif-col')).x, 170);
  near((await box(page, '.mif-col')).width, (1100 - 24) / 3);
  near((await box(page, '.mif-col')).height, 300);
  near((await box(page, '.mif-opts')).width, 1100);
  expect(await lbox(page.getByRole('button', { name: '웹 검색 후 정제로' }))).toMatchObject({ h: 48, y: 780 });
  await page.getByRole('button', { name: '웹 검색 후 정제로' }).click();

  // ── 웹 검색(단계 카드 · 같은 ② 팝업) → ③ 정제 팝업(?step=refine)
  await expect(page.getByRole('heading', { level: 1, name: '웹에서 찾는 중이에요' })).toBeVisible();
  await expect(page.getByRole('heading', { level: 1, name: '찾은 정보를 정리해요' })).toBeVisible({ timeout: 30_000 });
  await expect(page).toHaveURL(/\?step=refine$/);
  await expect(stepDlg.locator('.fl-shead__pos')).toHaveText('단계 3/3');
  await expect(page.getByTestId('mif-count')).toHaveText('찾은 13 · 담음 13');
  await expect(page.locator('.mif-tab')).toHaveText(['시장5/5', '고객사4/4', '사용자4/4']);
  await expect(page.locator('.mif-tag')).toHaveCount(0);                               // 처음 만들 때는 v1에서 유지 / 새로 찾음 표시가 없다
  await expect(stepDlg.getByRole('button', { name: 'MI 저장', exact: true })).toBeVisible();
  // 「‹ 검색어 고치기」 → ② 검색 팝업 → 다시 웹 검색 → ③
  await stepDlg.getByRole('button', { name: '검색어 고치기' }).click();
  await expect(page).toHaveURL(/\?step=search$/);
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible();
  await page.getByRole('button', { name: '웹 검색 후 정제로' }).click();
  await expect(page.getByRole('heading', { level: 1, name: '찾은 정보를 정리해요' })).toBeVisible({ timeout: 30_000 });
  await expect(page).toHaveURL(/\?step=refine$/);
  await expect(page.getByTestId('mif-count')).toHaveText('찾은 13 · 담음 13');
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
  await expect(orig).toHaveCount(0);
  await expect(stepDlg).toBeVisible();                                                  // 원문 창의 닫기는 단계 팝업을 닫지 않는다
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
  // 팝업 기준 칸(보드 MI3: 목록 1100 · 줄 76 · 체크 22 · 탭 34 · 원문 30 · 저장 h48 y780)
  near((await box(page, '.mif-list')).width, 1100);
  near((await box(page, '.mif-list')).x, 170);
  near((await box(page, '.mif-row')).height, 76);
  near((await box(page, '.mif-chk')).width, 22);
  near((await box(page, '.mif-tab')).height, 34);
  near((await box(page, '.mif-ghost30')).height, 30);
  expect(await lbox(stepDlg.getByRole('button', { name: 'MI 저장', exact: true }))).toMatchObject({ h: 48, y: 780 });
  await page.mouse.move(10, 890);
  await shot(page, 'MI3-first-new');

  // ── 저장 v1 → 팝업이 닫히고 같은 주소의 최종본(보드 MI_View · 완료 안내 화면 없음)
  await stepDlg.getByRole('button', { name: 'MI 저장', exact: true }).click();
  await expect(stepDlg).toHaveCount(0, { timeout: 20_000 });
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${MID}$`));
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'saved');
  await expect(view.locator('.fl-dver')).toHaveText(`${CODE} v1`);
  await expect(view.locator('.fl-dhead__meta')).toHaveText(/ 저장 · 담은 정보 11 \(찾은 13\) · 수치 원문 확인 2$/);
  await expect(view.locator('.fl-dnav__label')).toHaveText('단계별 고치기');
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(CODE);
  await expect(page.getByRole('heading', { name: 'MI를 저장했어요' })).toHaveCount(0);
  await expect(view.locator('.fl-slot')).toHaveCount(0);
  await expect(view.locator('.fl-dfollow')).toHaveCount(0);                            // MI 는 후속 작업이 없다
  await expect(view.locator('.miv-chip')).toHaveText(['최근 1년', '뉴스', '공시 · IR', '리포트', '정부 통계']);
  await expect(view.locator('.miv-bar__q')).toHaveText('시장 4 · 고객사 3 · 사용자 3 · 프라임 오피스 스마트 빌딩 도입 외');
  await expect(view.locator('.miv-col__t')).toHaveText(['시장', '고객사', '사용자']);
  await expect(view.locator('.miv-col__n')).toHaveText(['3', '4', '4']);
  await expect(view.locator('[data-vcol="market"] .miv-item__t').first()).toHaveText('프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석');
  await expect(view.locator('[data-vcol="market"] .miv-item').filter({ hasText: '공실률' })).toHaveCount(0);   // 뺀 것은 안 보인다
  await expect(view.locator('[data-vcol="customer"] .miv-item').filter({ hasText: '에너지 사용을' }).locator('.miv-item__meta')).toContainText('공시 · IR지속가능경영보고서 · 2026-04');
  await expect(view.locator('.miv-item .fl-vtag--warn')).toHaveCount(2);                // 수치 원문 확인(담은 것만)
  await expect(view.locator('.miv-foot')).toHaveText('문장은 원문을 줄여 쓴 것이에요 · 수치는 원문에서 확인해요');
  // 보드 View(content=mi): 줄 1100 × 44 · 3열 (1100 − 24) / 3 · 머리 44 + 선
  expect(await lbox(view.locator('.miv-bar'))).toMatchObject({ w: 1100, h: 44, x: 300 });
  near((await box(page, '.miv-col')).width, (1100 - 24) / 3);
  near((await box(page, '.miv-col')).x, 300);
  near((await box(page, '.miv-col__head')).height, 45);
  near((await box(page, '.miv-chip')).height, 24);
  // 최종본의 원문(URL 없음) → 검색 결과 글
  await view.locator('[data-vcol="market"] .miv-item').first().getByRole('button', { name: /^원문 · / }).click();
  await expect(page.getByRole('dialog', { name: '원문 · 검색 결과' })).toContainText('부동산 리서치 2026-08 리포트에 따르면');
  await page.getByRole('dialog', { name: '원문 · 검색 결과' }).getByRole('button', { name: '닫기' }).last().click();
  let flow = await hub(request, SB.id);
  expect(flow.stages.mi.ref).toBe(CODE);
  expect(flow.stages.mi.ver).toBe(1);
  expect(flow.stages.mi.counts).toEqual({ found: 13, kept: 11, numberCheck: 2 });
  expect(flow.stages.mi.items).toHaveLength(11);
  expect(flow.stages.mi.items[0].summary).toBe('프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석');
  expect(flow.stages.mi.items[0].source).toEqual({ type: '리포트', name: '부동산 리서치', date: '2026-08', url: null });
  expect(flow.stages.mi.filters.sourceTypes).toContain('정부 통계');
  expect(flow.cells.find((c: { key: string }) => c.key === 'mi').route).toBe(`/mi/flow/${MID}`);
  await page.mouse.move(10, 890);
  await shot(page, 'MI_View-v1-new');
  // 새로 고침해도 최종본(저장된 것은 팝업을 열지 않는다)
  await page.reload();
  await expect(view).toHaveAttribute('data-status', 'saved');
  await expect(stepDlg).toHaveCount(0);
  // flow.json(stages.mi 강조)
  await view.getByRole('button', { name: 'flow.json' }).click();
  const json = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(json).toBeVisible();
  await expect(json.locator('.wm-jsonline--add').first()).toContainText('"mi": {');
  await shot(page, 'MI_ViewJson-new');
  await json.getByRole('button', { name: '닫기' }).last().click();

  // ── 단계 칩 「정제」 → 고치기 팝업(MI3 고치기: MI-nn v1 고치기 · MI 저장 · v2) — 고치지 않고 닫으면 묻지 않는다
  await view.getByRole('button', { name: /^정제 · / }).click();
  await expect(page).toHaveURL(/\?step=refine$/);
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText(`${CODE} v1 고치기`);
  await expect(stepDlg.locator('.fl-shead__note')).toHaveText(`저장하면 ${CODE} v2 · ${SB.id}에 반영돼요`);
  await expect(stepDlg.getByRole('button', { name: 'MI 저장 · v2' })).toBeVisible();
  await expect(row(page, '업계 분석').locator('.mif-tag')).toHaveText('v1에서 유지');
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(stepDlg).toHaveCount(0);
  await expect(page.getByRole('dialog', { name: '고친 내용을 저장할까요?' })).toHaveCount(0);

  // ── 단계 칩 「검색」 → 고치기 팝업 · Storyboard 다시 읽기(보드 MI2_Loading: 「MI-01 v1 고치기」 · 「저장하면 MI-01 v2 · SB에 반영돼요」)
  await view.getByRole('button', { name: /^검색 · / }).click();
  await expect(page).toHaveURL(/\?step=search$/);
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText(`${CODE} v1 고치기`);
  await expect(stepDlg.locator('.fl-shead__note')).toHaveText(`저장하면 ${CODE} v2 · ${SB.id}에 반영돼요`);
  await expect(page.getByRole('heading', { level: 1, name: 'Storyboard를 읽는 중이에요' })).toBeVisible();
  const steps = page.getByTestId('mif-steps');
  await expect(steps.locator('.mif-step[data-state="run"]')).toHaveText(/고객사 · 업종 · 공간 · 요구 뽑기/, { timeout: 10_000 });
  await expect(steps.locator('.mif-step').first()).toContainText('요구사항 · DSS · 요약본');
  await page.mouse.move(10, 890);
  await page.screenshot({ path: 'e2e/mi/__screens__/MI2_Loading-new.png' });
  // 폭: 본문 1180 · 단계 카드 = 1180 − 40×2 · 줄 44 + 선
  near((await box(page, '.mif-screen')).width, 1180);
  near((await box(page, '.mif-steps')).width, 1100);
  near((await box(page, '.mif-steps')).x, 170);
  near((await box(page, '.mif-step')).height, 45);

  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.mif-opt__k')).toHaveText(['기간', '출처', `기존 ${CODE}`]);
  await expect(page.getByRole('group', { name: `기존 ${CODE}` }).getByRole('button', { name: '담은 정보 11개 유지 · 새로 찾은 것만 더하기' })).toHaveAttribute('aria-pressed', 'true');
  // 보드 MI2 모양: 「건물 에너지 효율 규제」 빼고 · 출처에서 정부 통계 빼고 → 검색어 9개
  await page.getByRole('button', { name: '빼기 · 건물 에너지 효율 규제' }).click();
  await page.getByRole('group', { name: '출처' }).getByRole('button', { name: '정부 통계' }).click();
  await expect(page.locator('.mif-foot .wm-flow__summary')).toHaveText('검색어 9개 · 1–2분');
  await page.mouse.move(10, 890);
  await shot(page, 'MI2-new');
  near((await box(page, '.mif-opt__k')).width, 96);
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

  // ── MI3 고치기(보드: 찾은 13 · 담음 12 · 시장 4/5 · v1에서 유지 / 새로 찾음)
  await expect(page.getByRole('heading', { level: 1, name: '찾은 정보를 정리해요' })).toBeVisible({ timeout: 30_000 });
  await expect(page).toHaveURL(/\?step=refine$/);
  await expect(page.getByTestId('mif-count')).toHaveText('찾은 13 · 담음 13');
  await expect(row(page, '업계 분석').locator('.mif-tag')).toHaveText('v1에서 유지');
  await expect(row(page, '공실률').locator('.mif-tag')).toHaveText('새로 찾음');
  await row(page, '건물 에너지 효율').getByRole('checkbox').click();
  await expect(page.getByTestId('mif-count')).toHaveText('찾은 13 · 담음 12');
  await expect(page.locator('.mif-tab')).toHaveText(['시장4/5', '고객사4/4', '사용자4/4']);
  await expect(page.locator('.mif-row .mif-tag')).toHaveText(['v1에서 유지', '새로 찾음', 'v1에서 유지', 'v1에서 유지', '새로 찾음']);   // 찾은 순서(보드 MI3 처럼 섞여 보인다)
  await expect(stepDlg.locator('.mif-foot .wm-flow__back')).toHaveText('검색어 고치기');
  await expect(stepDlg.getByRole('button', { name: 'MI 저장 · v2' })).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'MI3-new');

  // ── 고친 뒤 닫으면 저장할지 묻는다 → 「저장 · v2」 → 최종본 v2(보드 MI_View)
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  const ask = page.getByRole('dialog', { name: '고친 내용을 저장할까요?' });
  await expect(ask).toBeVisible();
  await expect(ask).toContainText(`저장하면 ${CODE} v2로 연결된 Storyboard에 반영돼요.`);
  await ask.getByRole('button', { name: '계속 고치기' }).click();
  await expect(ask).toHaveCount(0);
  await expect(stepDlg).toBeVisible();
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(ask).toBeVisible();
  await ask.getByRole('button', { name: '저장 · v2' }).click();
  await expect(stepDlg).toHaveCount(0, { timeout: 20_000 });
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${MID}$`));
  await expect(view.locator('.fl-dver')).toHaveText(`${CODE} v2`);
  await expect(view.locator('.fl-dhead__meta')).toHaveText(/ 저장 · 담은 정보 12 \(찾은 13\) · 수치 원문 확인 3$/);
  await expect(view.locator('.miv-col__n')).toHaveText(['4', '4', '4']);
  await expect(view.locator('.miv-chip')).toHaveText(['최근 1년', '뉴스', '공시 · IR', '리포트', '정부 통계']);
  await expect(view.locator('.miv-bar__q')).toHaveText('시장 4 · 고객사 3 · 사용자 3 · 프라임 오피스 스마트 빌딩 도입 외');
  await page.mouse.move(10, 890);
  await shot(page, 'MI_View-new');
  flow = await hub(request, SB.id);
  expect(flow.stages.mi.ver).toBe(2);
  expect(flow.stages.mi.prevVer).toBe(1);
  expect(flow.stages.mi.counts).toEqual({ found: 13, kept: 12, numberCheck: 3 });
  expect(flow.stages.mi.items.map((x: { addedIn: string }) => x.addedIn).filter((v: string) => v === 'v2')).toHaveLength(1);
  expect(flow.stages.mi.queries.user).toEqual(['하이브리드 근무 회의실 수요', '오피스 방문객 출입 경험', '임차인 선호 오피스 설비']);   // 뺀 검색어는 안 들어간다

  // ── 목록에 저장된 MI(허브) — 연결된 Storyboard 칩
  await page.goto('/mi');
  const line = page.locator('.fl-card', { hasText: `${CODE} v2` });
  await expect(line).toHaveCount(1);
  await expect(line.locator('.fl-sbchip')).toHaveText(SB.name);
  await expect(line.locator('.fl-cardtitle')).toHaveAttribute('href', `/mi/flow/${MID}`);
  await shot(page, 'MI0-new');
});

test('MI1 · MI1_Branch — 이미 MI 가 있는 Storyboard → 「수정」은 ② 고치기 팝업 · 「복제본 만들기」는 분기 Storyboard 에 새 MI', async ({ page, request }) => {
  test.setTimeout(120_000);
  test.skip(!SB.id || !CODE, '앞 테스트가 만든 Storyboard 가 필요해요');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/mi/new?sb=${SB.id}`);
  const mine = page.getByRole('radio', { name: new RegExp(SB.name) }).first();
  await expect(mine).toHaveAttribute('aria-checked', 'true');
  await expect(mine).toContainText(`${CODE} v2 있음`);
  await expect(page.locator('.fl-exist')).toContainText(`이 Storyboard에는 MI ${CODE} v2가 이미 있어요`);
  await expect(page.getByRole('button', { name: `${CODE} 수정하기` })).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'MI1-edit-new');
  // 수정 → 그 MI 의 ② 검색 고치기 팝업(Storyboard 다시 읽기)
  await page.getByRole('button', { name: `${CODE} 수정하기` }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${MID}\\?step=search$`));
  const stepDlg = page.locator('.fl-stepdlg');
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText(`${CODE} v2 고치기`);
  await expect(page.getByRole('heading', { level: 1, name: 'Storyboard를 읽는 중이에요' })).toBeVisible();
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(stepDlg).toHaveCount(0);
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'saved');
  await expect(page.locator('.fl-detail .fl-dver')).toHaveText(`${CODE} v2`);

  // 복제본 만들기 → 분기 Storyboard 에 새 MI(② 검색 팝업)
  await page.goto(`/mi/new?sb=${SB.id}`);
  await page.getByRole('radio', { name: /복제본 만들기/ }).click();
  await expect(page.getByRole('button', { name: /분기 만들고 시작/ })).toBeVisible();
  await expect(page.locator('.fl-gatefoot')).toContainText(`‘${SB.name} · 분기 B’가 새로 생겨요`);
  await page.mouse.move(10, 890);
  await shot(page, 'MI1_Branch-new');
  await page.getByRole('button', { name: /분기 만들고 시작/ }).click();
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}\?step=search$/);
  const bid = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  const d = await (await request.get(`/api/mi/v1/mi-flows/${bid}`)).json();
  expect(d.code).not.toBe(CODE);
  expect(d.sb_id).not.toBe(SB.id);
  const b = await hub(request, d.sb_id);
  expect(b.parent).toBe(SB.id);
  await expect(stepDlg.locator('.fl-shead__sb')).toContainText(b.name);
  await expect(page.locator('.fl-detail .wm-sbbar__chip')).toContainText(b.name);
  await expect(page.locator('.fl-detail .wm-sbbar__branch')).toHaveText('분기');
  // 원본 MI 는 그대로
  expect((await hub(request, SB.id)).stages.mi.ref).toBe(CODE);
});

test('Storyboard 「만들기」(?sb=&auto=1) → Gate 없이 ② 분석 로딩 · 닫으면 작성 중 최종본(MI_Draft) · 이전 흐름 링크(?rq=) → /mi/legacy/new', async ({ page, request }) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });
  await page.goto(`/mi/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}\?step=search$/);
  const id = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  await expect(page.getByRole('heading', { level: 1, name: 'Storyboard를 읽는 중이에요' })).toBeVisible();
  const stepDlg = page.locator('.fl-stepdlg');
  await expect(stepDlg.locator('.fl-shead__note')).toHaveText('MI를 저장하면 이 Storyboard에 연결돼요');
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText('새로 만들기');
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'new');
  await page.mouse.move(10, 890);
  await shot(page, 'MI2_Loading-first-new');
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible({ timeout: 20_000 });
  // 1920 × 1080: 팝업은 가운데 1180 × 800 그대로 · 검색어 칸 (1100 − 24) / 3
  await page.setViewportSize({ width: 1920, height: 1080 });
  expect(await lbox(stepDlg)).toMatchObject({ x: 370, y: 140, w: 1180, h: 800 });
  near((await box(page, '.mif-col')).width, (1100 - 24) / 3);
  await page.setViewportSize({ width: 1440, height: 900 });

  // 닫으면 작성 중 최종본(보드 MI_Draft: 작성 중 1/3 · ② 자리표시에 「이어서 · 검색」 · ③ 큰 자리표시)
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(stepDlg).toHaveCount(0);
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'draft');
  await expect(view.locator('.fl-dver')).toHaveText('작성 중 1/3');
  await expect(view.locator('.fl-dhead__meta')).toHaveText(`작성 중 · 3단계 중 1단계 마침 · 저장하면 ${sb.id}에 연결돼요`);
  await expect(view.locator('.fl-dnav__label')).toHaveText('단계 1/3');
  await expect(view.locator('[data-slot="2"]').getByRole('button', { name: '이어서 · 검색' })).toBeVisible();
  await expect(view.locator('[data-slot="3"]')).toContainText('시장 · 고객사 · 사용자별로 담은 정보 — 앞 단계를 마치면 열려요');
  await expect(view.locator('[data-slot="3"]').getByRole('button')).toHaveCount(0);
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(`${sb.name} 시장 분석`);
  near((await box(page, '[data-slot="3"]')).width, 1100);
  expect((await box(page, '[data-slot="3"]')).height).toBeGreaterThan(400);            // ③ 은 남은 높이를 채운다(보드 MI_Draft)
  await page.mouse.move(10, 890);
  await shot(page, 'MI_Draft-new');
  await view.locator('[data-slot="2"]').getByRole('button', { name: '이어서 · 검색' }).click();
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${id}\\?step=search$`));
  await expect(page.getByRole('heading', { level: 1, name: '무엇을 검색할까요?' })).toBeVisible();

  // DSS 전 Storyboard 는 Gate 에서 고를 수 없다(점선 · DSS 먼저)
  const pre = await makeStoryboard(request, { name: `판교 스타트업 단지 ${tag()}` });
  await page.goto(`/mi/new?sb=${pre.id}&auto=1`);
  const off = page.getByRole('radio', { name: new RegExp(pre.name) });
  await expect(off).toHaveAttribute('aria-disabled', 'true');
  await expect(off).toContainText('DSS 먼저');
  await expect(page).toHaveURL(/\/mi\/new\?/);
  // 고르기 전에 닫으면 목록
  await page.locator('.fl-stepdlg').getByRole('button', { name: '팝업 닫기' }).click();
  await expect(page).toHaveURL(/\/mi$/);
  // 요구사항 정의서의 「Market Intelligence」(이전 흐름) 링크
  await page.goto('/mi/new?rq=rq_TEST');
  await expect(page).toHaveURL(/\/mi\/legacy\/new\?rq=rq_TEST$/);
  expect((await request.delete(`/api/mi/v1/mi-flows/${id}`)).status()).toBe(204);    // 정리
});
