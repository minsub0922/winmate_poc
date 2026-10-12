/**
 * MI — 웹앱 ① v63 「최종본에서 바로 고치기」(보드 webapp1 MI0 · MI1 · MI1_Branch · MI2_Loading · MI2 · MI2_Run · MI3 · MI3_Edit · MI_View · MI_Search · MI_Draft)
 * — docs/scenarios/11-content-flow.md §1 · §6 · docs/handoff/2026-10-12-content-detail-v63.md.
 * 실제 스택: 게이트웨이 → mi(+워커) · storyboard 허브 · ai-tools(mock 고정 응답 mocks/ai-tools/mi.flow_analyze.v1 · mi.flow_search.v1 = 보드 예시 문장).
 * 목록 → 「새 MI 만들기」 → 목록 위 팝업에서 Storyboard 고르기 → 상세 한 장(새로 만들기) + 바로 검색 팝업(AI 분석 로딩 → 검색어 · 조건) → 웹 검색
 * → 같은 화면 찾는 중(뼈대) → 찾은 정보가 세 칸에 → 빼기 · 문장 고치기 → 저장(그 자리에서 저장됨 · 토스트) → 하나 빼기 「고친 곳 1」 → 되돌리기
 * → 다시 검색(검색어 · 조건 고치고 다시 검색 · 담은 정보 유지 · 새로 찾은 것만) · 고치고 저장 · v2.
 * 보드 고정 칸(본문 1180 → 1100 · 팝업 1040×740 · 세 칸 (1100 − 24)/3 · 띠 48 · 검색어 칸 h280)을 숫자로 재고 __screens__/<보드>.png 를 남긴다.
 * 실행: make e2e-feature SERVICE=mi (또는 WM_E2E_SUITE=mi WM_E2E_DEV=1 WM_E2E_PORT=5203 npx playwright test e2e/mi/mi-flow.spec.ts --workers=1)
 */
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { shot } from './helpers';

test.describe.configure({ mode: 'serial' });

const box = async (l: Locator) => (await l.first().boundingBox())!;
const near = (got: number, want: number, tol = 0.6) => expect(Math.abs(got - want), `${got} ≈ ${want}`).toBeLessThanOrEqual(tol);

async function hub(request: APIRequestContext, sbId: string) {
  const r = await request.get(`/api/storyboard/v1/flows/${sbId}`);
  expect(r.ok()).toBeTruthy();
  return r.json();
}
const getDoc = async (request: APIRequestContext, id: string) => (await request.get(`/api/mi/v1/mi-flows/${id}`)).json();

/** 찾은 정보 줄(요약 문장으로) */
const item = (page: Page, text: string | RegExp) => page.locator('.mif-item').filter({ hasText: text });
const col = (page: Page, g: 'market' | 'customer' | 'user') => page.locator(`.mif-gcol[data-group="${g}"]`);
/** 머리(보드 View) */
const head = (page: Page) => page.locator('.cd-head');

let SB = { id: '', name: '' };
let CODE = '';

test('새 MI v63 — 목록 → 팝업 → 상세 + 검색 팝업(분석 → 검색어) → 웹 검색 → 찾은 정보 그 자리에서 → 저장 → 고친 곳 · 되돌리기 → 다시 검색 · v2', async ({ page, request }) => {
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  SB = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });

  // ── MI0 목록(보드 List content=mi) → 「새 MI 만들기」 → 목록 위 팝업(보드 MI1 = Gate)
  await page.goto('/mi');
  await expect(page.getByRole('heading', { level: 1, name: 'Market Intelligence' })).toBeVisible();
  await expect(page.getByText('사전 작업 · 최소 DSS까지 된 Storyboard')).toBeVisible();
  await page.getByRole('link', { name: /새 MI 만들기/ }).click();
  await expect(page).toHaveURL(/\/mi\/new$/);
  const gate = page.getByRole('dialog', { name: '새 MI 만들기 · Storyboard 고르기' });
  await expect(gate.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  const mine = gate.getByRole('radio', { name: new RegExp(SB.name) });
  await mine.click();
  await expect(mine).toHaveAttribute('aria-checked', 'true');
  await page.mouse.move(10, 890);
  await shot(page, 'MI1');
  await gate.getByRole('button', { name: /이 Storyboard로 시작/ }).click();

  // ── MI2_Loading — 상세(새로 만들기) 위에 바로 검색 팝업 · AI 가 Storyboard 를 먼저 읽는다(CF-08 의 MI 예외)
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}$/);
  const mid = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  const pop = page.getByRole('dialog', { name: 'MI 검색' });
  await expect(pop).toBeVisible();
  await expect(pop.locator('.mis-h1')).toHaveText('Storyboard를 읽는 중이에요');
  await expect(pop.getByTestId('mif-steps')).toContainText(`Storyboard ${SB.id} 읽기`);
  await expect(pop.getByText('AI가 Storyboard를 분석하고 있어요')).toBeVisible();
  await expect(pop.getByRole('button', { name: '웹 검색' })).toBeDisabled();
  await expect(pop.locator('.mis-footline')).toHaveText('분석이 끝나면 웹 검색을 시작할 수 있어요');
  await expect(pop.locator('.mis-sb')).toHaveText(SB.name);
  // 뒤: 상세 머리(새로 만들기) · 띠 점선 안내 · 세 칸 자리
  await expect(head(page).locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(head(page).locator('.cd-meta')).toHaveText(`새로 만드는 중 · 쓰는 대로 작성 중으로 남아요 · 저장하면 ${SB.id}에 연결돼요`);
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새로 만들기');
  await expect(pop.locator('.mis-step[data-state="run"]')).toHaveText(/고객사 · 업종 · 공간 · 요구 뽑기/, { timeout: 10_000 });
  await expect(pop.locator('.mis-step').first()).toContainText('요구사항 · DSS · 요약본');
  await shot(page, 'MI2_Loading');
  // 팝업 1040×740 · 머리 72 · 아래 줄 76 · 단계 줄 44(+선)
  const pb = await box(pop);
  near(pb.width, 1040);
  near(pb.height, 740);
  near((await box(pop.locator('.mis-head'))).height, 72);
  near((await box(pop.locator('.mis-foot'))).height, 76);
  near((await box(pop.locator('.mis-step'))).height, 45);
  near((await box(pop.locator('.mis-steps'))).width, 1040 - 48);
  // 딤은 화면 전체(1440×900)를 덮고 팝업은 가운데
  const scrim = await box(page.locator('.wm-scrim').filter({ has: pop }));
  near(scrim.x, 0); near(scrim.width, 1440); near(scrim.height, 900);
  near(pb.x, (1440 - 1040) / 2); near(pb.y, (900 - 740) / 2);

  // ── MI2 — 검색어 · 검색 조건
  await expect(pop.locator('.mis-h1')).toHaveText('무엇을 검색할까요?', { timeout: 20_000 });
  await expect(pop.locator('.mis-basis')).toContainText('AI 분석');
  await expect(pop.locator('.mis-basis__chip')).toHaveText(['고객사E 자산운용', '업종오피스 · 업무시설', '공간로비 외 2', '요구에너지 절감 · AI Ready']);
  await expect(pop.locator('.mis-col__t')).toHaveText(['시장', '고객사', '사용자']);
  await expect(pop.locator('.mis-col__n')).toHaveText(['검색어 4', '검색어 3', '검색어 3']);
  await expect(pop.locator('.mis-opt__k')).toHaveText(['기간', '출처']);           // 처음 만들 때는 「기존 MI」 줄이 없다
  CODE = (await getDoc(request, mid)).code;
  // 보드 MI2 모양: 「건물 에너지 효율 규제」 빼기 → 검색어 9개
  await pop.getByRole('button', { name: '빼기 · 건물 에너지 효율 규제' }).click();
  await expect(pop.locator('.mis-q--off')).toHaveText('건물 에너지 효율 규제');
  await expect(pop.locator('.mis-footline')).toHaveText('검색어 9개 · 1–2분 · 찾은 정보는 MI 화면에 바로 모이고, 거기서 담을 것을 골라요');
  await page.mouse.move(10, 890);
  await shot(page, 'MI2');
  // 검색어 세 칸 = (1040 − 48 − 24) / 3 · 높이 280 · 조건 키 96 · 검색어 34 · 칩 30 · 웹 검색 46
  const qcols = pop.locator('.mis-col');
  for (let i = 0; i < 3; i += 1) {
    const b = (await qcols.nth(i).boundingBox())!;
    near(b.width, (1040 - 48 - 24) / 3);
    near(b.height, 280);
  }
  near((await box(pop.locator('.mis-opt__k'))).width, 96);
  near((await box(pop.locator('.mis-q'))).height, 34);
  near((await box(pop.locator('.mis-chip'))).height, 30);
  near((await box(pop.getByRole('button', { name: '웹 검색' }))).height, 46);
  // 더하기 · 다시 넣기 · 조건(정부 통계 더하기 → 출처 4)
  await pop.getByLabel('사용자 검색어 추가').fill('오피스 라운지 이용 행태');
  await pop.getByLabel('사용자 검색어 추가').press('Enter');
  await expect(pop.locator('[data-group="user"] .mis-q')).toHaveCount(4);
  await pop.getByRole('button', { name: '빼기 · 오피스 라운지 이용 행태' }).click();
  await pop.getByRole('button', { name: '다시 넣기 · 건물 에너지 효율 규제' }).click();
  await pop.getByRole('group', { name: '출처' }).getByRole('button', { name: '정부 통계' }).click();
  await expect(pop.getByRole('group', { name: '출처' }).getByRole('button', { name: '정부 통계' })).toHaveAttribute('aria-pressed', 'true');
  await expect(pop.locator('.mis-footline')).toContainText('검색어 10개 · 1–2분');
  await expect.poll(async () => (await getDoc(request, mid)).filters.sourceTypes).toEqual(['뉴스', '공시 · IR', '리포트', '정부 통계']);

  // ── 웹 검색 → 팝업 닫힘 · 같은 화면 찾는 중(MI2_Run: 띠 「웹에서 찾는 중 · 1–2분」 · 세 칸 뼈대)
  await pop.getByRole('button', { name: '웹 검색' }).click();
  await expect(pop).toHaveCount(0);
  const strip = page.getByTestId('mif-strip');
  await expect(strip.locator('.mif-strip__run')).toHaveText('웹에서 찾는 중 · 1–2분');
  await expect(strip.locator('.mif-run')).toHaveCount(0);                              // 찾는 중에는 버튼이 없다
  await expect(page.locator('.mif-gcol__sub')).toHaveText(['찾는 중', '찾는 중', '찾는 중']);
  await expect(page.locator('.mif-gcol[data-group="market"] .mif-skel')).toHaveCount(3);
  await page.mouse.move(10, 890);
  await shot(page, 'MI2_Run');

  // ── MI3 — 찾은 정보가 세 칸에(그 자리에서 담기 · 빼기 · 문장 고치기)
  await expect(strip.locator('.mif-run')).toHaveText('검색어 · 조건 고치고 다시 검색', { timeout: 30_000 });
  await expect(strip.locator('.mif-strip__chip')).toHaveText(['최근 1년', '뉴스', '공시 · IR', '리포트', '정부 통계']);
  await expect(strip.locator('.mif-strip__q')).toHaveText('시장 4 · 고객사 3 · 사용자 3 — 프라임 오피스 스마트 빌딩 도입 · E 자산운용 용산 재개발 · 하이브리드 근무 회의실 수요 외');
  await expect(page.locator('.mif-gcol__n')).toHaveText(['5/5', '4/4', '4/4']);
  await expect(page.locator('.mif-gcol__sub')).toHaveText(['담음 5', '담음 4', '담음 4']);
  await expect(page.locator('.mif-item .mif-tag')).toHaveCount(13);
  await expect(page.locator('.mif-item .mif-tag').first()).toHaveText('새로 찾음');
  const first = item(page, '프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다.');
  await expect(first.locator('.mif-kind')).toHaveText('리포트');
  await expect(first.locator('.mif-src')).toHaveText('부동산 리서치 · 2026-08');
  await expect(item(page, '공실률').locator('.mif-numchk')).toHaveText('수치 원문 확인');
  await expect(item(page, '건물 에너지 효율').locator('.mif-kind')).toHaveText('정부 통계');
  await expect(head(page).locator('.cd-meta')).toHaveText(`새로 만드는 중 · 쓰는 대로 작성 중으로 남아요 · 저장하면 ${SB.id}에 연결돼요`);
  // 원문(요약형 검색 — URL 없음 → 검색 결과 글)
  await first.getByRole('button', { name: '원문' }).click();
  const orig = page.getByRole('dialog', { name: '원문 · 검색 결과' });
  await expect(orig).toContainText('프라임 오피스 스마트 빌딩 도입');
  await expect(orig).toContainText('부동산 리서치 2026-08 리포트에 따르면');
  await orig.getByRole('button', { name: '닫기' }).last().click();
  // 문장을 눌러 바로 고치기(글 칸 · 떠날 때 저장)
  await first.getByRole('button', { name: /^문장 고치기 · / }).click();
  const ed = page.getByLabel('정리 문장');
  await expect(ed).toBeFocused();
  near((await box(ed)).height, 62);
  await ed.fill('프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석');
  await ed.blur();
  await expect(item(page, '업계 분석')).toHaveCount(1);
  await expect.poll(async () => (await getDoc(request, mid)).items.find((x: { summary: string }) => x.summary.endsWith('업계 분석'))?.edited).toBe(true);
  // 빼기(정부 통계) → 흐리게 · 취소선 · 아래로 · 4/5
  await item(page, '건물 에너지 효율').getByRole('checkbox').click();
  await expect(col(page, 'market').locator('.mif-gcol__n')).toHaveText('4/5');
  await expect(col(page, 'market').locator('.mif-item').last()).toContainText('건물 에너지 효율');
  await expect(item(page, '건물 에너지 효율').locator('.mif-item__t')).toHaveCSS('text-decoration-line', 'line-through');
  await expect(head(page).locator('.cd-chg')).toHaveCount(0);                         // 저장 전에는 고친 곳을 세지 않는다
  await page.mouse.move(10, 890);
  await shot(page, 'MI3');
  // 폭: 본문 열 1180 → 본문 1100 · 세 칸 같은 폭 (1100 − 24) / 3 · 띠 48 · 칸 머리 44(+선) · 체크 20 · 버튼 36 · 저장 42
  near((await box(page.locator('.wm-flow'))).width, 1180);
  near((await box(page.locator('.mif-body'))).width, 1100);
  near((await box(strip)).height, 48);
  const gcols = page.locator('.mif-gcol');
  const widths = [];
  for (let i = 0; i < 3; i += 1) widths.push((await gcols.nth(i).boundingBox())!.width);
  for (const w of widths) near(w, (1100 - 24) / 3);
  near((await box(page.locator('.mif-gcol__head'))).height, 45);
  near((await box(page.locator('.mif-box'))).width, 20);
  near((await box(strip.locator('.mif-run'))).height, 36);
  near((await box(head(page).getByRole('button', { name: '저장', exact: true }))).height, 42);
  // 머리 · 본문 · 각주 위치(보드: 머리 46 · 띠는 머리 아래 14 · 각주는 본문 아래)
  const hb = await box(head(page));
  const sbx = await box(strip);
  near(sbx.y - (hb.y + hb.height), 14);

  // ── 저장 v1 → 그 자리에서 저장됨(MI_View) · 토스트 · 완료 화면 없음
  await head(page).getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: `${CODE} v1 저장 · 담은 정보 12` })).toBeVisible();
  await expect(head(page).locator('.cd-ref')).toHaveText(`${CODE} v1`);
  await expect(head(page).locator('.cd-meta')).toHaveText(/^오늘 \d\d:\d\d 저장 · 담은 정보 12 \(찾은 13\) · 수치 원문 확인 3$/);
  await expect(head(page).locator('.cd-hint')).toHaveText('눌러서 바로 고쳐요');
  await expect(head(page).getByRole('button', { name: /flow\.json/ })).toBeVisible();
  await expect(head(page).getByRole('button', { name: '저장', exact: true })).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/mi/flow/${mid}$`));
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(CODE);
  await expect(page.locator('.mif-item .mif-tag')).toHaveCount(0);                    // v1 은 표시 없음(보드 MI_View: 다음 판에서 찾은 것만 「vN에서 찾음」)
  let flow = await hub(request, SB.id);
  expect(flow.stages.mi.ref).toBe(CODE);
  expect(flow.stages.mi.ver).toBe(1);
  expect(flow.stages.mi.counts).toEqual({ found: 13, kept: 12, numberCheck: 3 });
  expect(flow.stages.mi.items[0].summary).toBe('프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석');
  expect(flow.stages.mi.items[0].source).toEqual({ type: '리포트', name: '부동산 리서치', date: '2026-08', url: null });
  expect(flow.cells.find((c: { key: string }) => c.key === 'mi').route).toBe(`/mi/flow/${mid}`);
  await page.mouse.move(10, 890);
  await expect(page.locator('.wm-toast')).toHaveCount(0, { timeout: 8000 });         // 토스트가 사라진 뒤
  await shot(page, 'MI_View');
  // 새로 고침해도 저장됨 · 예전 완료 주소(?done=1)도 상세
  await page.goto(`/mi/flow/${mid}?done=1`);
  await expect(head(page).locator('.cd-ref')).toHaveText(`${CODE} v1`);
  await expect(page.getByRole('dialog', { name: 'MI 검색' })).toHaveCount(0);

  // ── 하나 빼기 → 「고친 곳 1」(MI3_Edit) · 줄 표시(안쪽 막대 · 「이번에 뺌」) → 되돌리기
  await item(page, '방문객').getByRole('checkbox').click();
  await expect(head(page).locator('.cd-chg')).toHaveText('고친 곳 1');
  await expect(head(page).locator('.cd-ref')).toHaveText(`${CODE} v1 · 고치는 중`);
  await expect(head(page).locator('.cd-meta')).toHaveText(`${CODE} v1 고치는 중 · 저장하면 v2 · ${SB.id}에 반영돼요`);
  await expect(head(page).getByRole('button', { name: '저장 · v2' })).toBeVisible();
  await expect(item(page, '방문객').locator('.mif-tag')).toHaveText('이번에 뺌');
  await expect(item(page, '방문객')).toHaveClass(/mif-item--chg/);
  await expect(page.locator('.wm-sbbar__note')).toHaveText('저장하면 반영돼요');
  await head(page).getByRole('button', { name: '되돌리기' }).click();
  await expect(page.getByRole('status').filter({ hasText: `${CODE} v1로 되돌렸어요` })).toBeVisible();
  await expect(head(page).locator('.cd-chg')).toHaveCount(0);
  await expect(head(page).locator('.cd-ref')).toHaveText(`${CODE} v1`);
  await expect(item(page, '방문객').getByRole('checkbox')).toHaveAttribute('aria-checked', 'true');
  await expect(item(page, '방문객')).not.toHaveClass(/mif-item--chg/);
  expect((await getDoc(request, mid)).changes).toBe(0);

  // ── 하나 빼기 + 문장 고치기 → 고친 곳 2(보드 MI3_Edit) → 캡처
  await item(page, '방문객').getByRole('checkbox').click();
  await item(page, '리모델링').getByRole('button', { name: /^문장 고치기 · / }).click();
  await page.getByLabel('정리 문장').fill('E 자산운용이 최근 오피스 리모델링에 투자를 늘리는 방향 — 용산 포함 여부 확인');
  await page.getByLabel('정리 문장').blur();
  await expect(head(page).locator('.cd-chg')).toHaveText('고친 곳 2');
  await expect(item(page, '용산 포함 여부 확인').locator('.mif-item__t')).toHaveClass(/cd-in--chg/);
  await expect(item(page, '방문객')).toHaveClass(/mif-item--chg/);
  await expect(col(page, 'user').locator('.mif-item').last()).toContainText('방문객');            // 뺀 줄은 아래로
  await expect(col(page, 'user').locator('.mif-gcol__n')).toHaveText('3/4');
  // 고친 문장 칸이 아래 줄(종류 · 출처)과 겹치지 않는다
  const tb = await box(item(page, '용산 포함 여부 확인').locator('.mif-item__t'));
  const mb = await box(item(page, '용산 포함 여부 확인').locator('.mif-item__meta'));
  expect(tb.y + tb.height).toBeLessThanOrEqual(mb.y);
  await page.mouse.move(10, 890);
  await expect(page.locator('.wm-toast')).toHaveCount(0, { timeout: 8000 });
  await shot(page, 'MI3_Edit');

  // ── 검색어 · 조건 고치고 다시 검색(MI_Search) — 「기존 MI · 담은 정보 n개 유지」 · 정부 통계 빼기 → 웹 검색 → 새로 찾은 것만 더함(지금 화면 그대로)
  await strip.getByRole('button', { name: '검색어 · 조건 고치고 다시 검색' }).click();
  const pop2 = page.getByRole('dialog', { name: 'MI 검색' });
  await expect(pop2.locator('.mis-h1')).toHaveText('검색어 · 조건 고치고 다시 검색');
  await expect(pop2.locator('.mis-opt__k')).toHaveText(['기간', '출처', `기존 ${CODE}`]);
  await expect(pop2.getByRole('group', { name: `기존 ${CODE}` }).getByRole('button', { name: '담은 정보 11개 유지 · 새로 찾은 것만 더하기' })).toHaveAttribute('aria-pressed', 'true');
  await pop2.getByRole('group', { name: '출처' }).getByRole('button', { name: '정부 통계' }).click();
  await pop2.getByRole('button', { name: '빼기 · 건물 에너지 효율 규제' }).click();
  await expect(pop2.locator('.mis-footline')).toContainText('검색어 9개 · 1–2분');
  await page.mouse.move(10, 890);
  await shot(page, 'MI_Search');
  near((await box(pop2)).width, 1040);
  near((await box(pop2)).height, 740);
  await pop2.getByRole('button', { name: '웹 검색' }).click();
  await expect(pop2).toHaveCount(0);
  await expect(strip.locator('.mif-strip__run')).toBeVisible();
  await expect(strip.locator('.mif-run')).toHaveText('검색어 · 조건 고치고 다시 검색', { timeout: 30_000 });
  // 고친 문장 · 뺀 것 그대로 · 검색어 · 조건이 바뀌어 고친 곳이 늘어난다
  await expect(item(page, '용산 포함 여부 확인')).toHaveCount(1);
  await expect(item(page, '방문객').getByRole('checkbox')).toHaveAttribute('aria-checked', 'false');
  await expect.poll(async () => (await getDoc(request, mid)).changes).toBeGreaterThan(2);

  // ── 저장 · v2 → 저장됨 v2 · 허브 반영
  await head(page).getByRole('button', { name: '저장 · v2' }).click();
  await expect(page.getByRole('status').filter({ hasText: `${CODE} v2 저장` })).toBeVisible();
  await expect(head(page).locator('.cd-ref')).toHaveText(`${CODE} v2`);
  await expect(head(page).locator('.cd-chg')).toHaveCount(0);
  await expect(item(page, '방문객')).not.toHaveClass(/mif-item--chg/);
  flow = await hub(request, SB.id);
  expect(flow.stages.mi.ver).toBe(2);
  expect(flow.stages.mi.prevVer).toBe(1);
  expect(flow.stages.mi.counts.kept).toBe(11);
  expect(flow.stages.mi.filters.sourceTypes).not.toContain('정부 통계');
  expect(flow.stages.mi.items.some((x: { summary: string }) => x.summary.includes('용산 포함 여부 확인'))).toBe(true);
  // flow.json 팝업(이 콘텐츠 줄 강조)
  await head(page).getByRole('button', { name: /flow\.json/ }).click();
  const json = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(json).toBeVisible();
  await expect(json.locator('.wm-jsonline--add').first()).toContainText('"mi": {');
  await json.getByRole('button', { name: '닫기' }).last().click();

  // ── 목록에 저장된 MI(허브) — 연결된 Storyboard 칩
  await page.goto('/mi');
  const card = page.locator('.fl-card', { hasText: `${CODE} v2` });
  await expect(card).toHaveCount(1);
  await expect(card.locator('.fl-sbchip')).toHaveText(SB.name);
  await expect(card.locator('.fl-cardtitle')).toHaveAttribute('href', `/mi/flow/${mid}`);
});

test('MI1_Branch — 이미 MI 가 있는 Storyboard → 복제본 만들기 → 분기 Storyboard 에 새 MI(검색 팝업)', async ({ page, request }) => {
  test.setTimeout(120_000);
  test.skip(!SB.id || !CODE, '앞 테스트가 만든 Storyboard 가 필요해요');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/mi/new?sb=${SB.id}`);
  const gate = page.getByRole('dialog', { name: '새 MI 만들기 · Storyboard 고르기' });
  const mine = gate.getByRole('radio', { name: new RegExp(SB.name) }).first();
  await expect(mine).toHaveAttribute('aria-checked', 'true');
  await expect(mine).toContainText(`${CODE} v2 있음`);
  await expect(gate.locator('.fl-exist')).toContainText(`이 Storyboard에는 MI ${CODE} v2가 이미 있어요`);
  await gate.getByRole('radio', { name: /복제본 만들기/ }).click();
  await expect(gate.getByRole('button', { name: /분기 만들고 시작/ })).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'MI1_Branch');
  await gate.getByRole('button', { name: /분기 만들고 시작/ }).click();
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}$/);
  const bid = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  const pop = page.getByRole('dialog', { name: 'MI 검색' });
  await expect(pop.locator('.mis-h1')).toHaveText('무엇을 검색할까요?', { timeout: 20_000 });
  const d = await getDoc(request, bid);
  expect(d.code).not.toBe(CODE);
  expect(d.sb_id).not.toBe(SB.id);
  const b = await hub(request, d.sb_id);
  expect(b.parent).toBe(SB.id);
  await pop.locator('.mis-close').click();
  await expect(page.locator('.wm-sbbar__chip')).toContainText(b.name);
  await expect(page.locator('.wm-sbbar__branch')).toHaveText('분기');
  // 원본 MI 는 그대로
  expect((await hub(request, SB.id)).stages.mi.ref).toBe(CODE);
});

test('Storyboard 「만들기」(?sb=&auto=1) → 바로 상세 + 검색 팝업 · 검색 전에 닫으면 작성 중(MI_Draft · 검색 시작) · 이전 흐름 링크(?rq=)', async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });
  await page.goto(`/mi/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/mi\/flow\/mif_[0-9A-Z]{26}$/);
  const id = page.url().match(/mif_[0-9A-Z]{26}/)![0];
  const pop = page.getByRole('dialog', { name: 'MI 검색' });
  await expect(pop).toBeVisible();
  await expect(page.locator('.wm-sbbar__note')).toHaveText('저장하면 이 Storyboard에 연결돼요 · 사전 작업에서 골랐어요');
  await expect(pop.locator('.mis-h1')).toHaveText('무엇을 검색할까요?', { timeout: 20_000 });
  // 검색 전에 닫기 → 작성 중(보드 MI_Draft: 「작성 중」 · 띠 검색 조건 · 검색어 · 주 버튼 「검색 시작」 · 세 칸 자리)
  await pop.locator('.mis-close').click();
  await expect(pop).toHaveCount(0);
  await expect(head(page).locator('.cd-ref')).toHaveText('작성 중');
  await expect(head(page).locator('.cd-meta')).toHaveText(new RegExp(`^작성 중 · 검색 전 · 오늘 \\d\\d:\\d\\d 자동 저장 · 저장하면 ${sb.id}에 연결돼요$`));
  const strip = page.getByTestId('mif-strip');
  await expect(strip.locator('.mif-strip__chip')).toHaveText(['최근 1년', '뉴스', '공시 · IR', '리포트']);
  await expect(strip.locator('.mif-strip__q')).toContainText('시장 4 · 고객사 3 · 사용자 3 — ');
  await expect(strip.locator('.mif-run')).toHaveText('검색 시작');
  await expect(strip.locator('.mif-run')).toHaveClass(/mif-run--primary/);
  await expect(page.locator('.mif-ph b')).toHaveText(['검색하면 여기에 모여요', '검색하면 여기에 모여요', '검색하면 여기에 모여요']);
  await expect(page.locator('.mif-ph span')).toHaveText(['업계 · 시장 동향', '고객사 사업 · 공시 · 보도', '공간을 쓰는 사람 · 수요 조사']);
  await page.mouse.move(10, 890);
  await shot(page, 'MI_Draft');
  // 찾은 정보 없이 저장하면 알려만 준다
  await head(page).getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: '웹 검색으로 찾은 정보를 담은 뒤 저장할 수 있어요' })).toBeVisible();
  // 새로 고침해도 작성 중(팝업은 저절로 열리지 않음) → 「검색 시작」은 팝업을 다시 연다
  await page.reload();
  await expect(head(page).locator('.cd-ref')).toHaveText('작성 중');
  await expect(page.getByRole('dialog', { name: 'MI 검색' })).toHaveCount(0);
  await strip.getByRole('button', { name: '검색 시작' }).click();
  await expect(page.getByRole('dialog', { name: 'MI 검색' }).locator('.mis-h1')).toHaveText('무엇을 검색할까요?');
  expect((await getDoc(request, id)).phase).toBe('search');
  // DSS 전 Storyboard 는 고를 수 없다(점선 · DSS 먼저)
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
