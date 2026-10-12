/**
 * 경쟁사 분석 — 웹앱 ① v63 「최종본에서 바로 고치기」(보드 webapp1 CA0 · CA1 · CA2 · CA_Draft · CA2_Info · CA2_Pc · CA2_AI · CA_View · CA2_Edit · CA_Table) — 실제 스택(mock 모델 · mocks/ai-tools/ca.flow_*.json).
 * Storyboard(rq → dss, API) → 목록 → 「새 경쟁사 분석 만들기」 → 목록 위 팝업에서 Storyboard 고르기 → 상세 한 장(새로 만들기 · 경쟁사 없음)
 * → 회사 이름으로 추가 · 판정 · 메모 바로 고치기 → 개요 · 장단점 탭 → AI 후보(점선) → 추가 → 저장(그 자리에서 저장됨 · 토스트)
 * → 판정 하나 고치기 「고친 곳 1」 → 되돌리기 → 고치고 저장 · v2 → 비교표(행 → 경쟁사별).
 * 보드 고정 칸(본문 1180 → 1100 · 목록 290 | 상세 796 · 비교 첫 칸 196 · 비교표 236 + 82×5)을 숫자로 재고, 화면을 __screens__/<보드>.png 로 남긴다.
 * 실행: make e2e-feature SERVICE=competitor (1 worker) · 이 파일만: … npx playwright test e2e/competitor/ca-flow.spec.ts --workers=1
 */
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { internalHeaders, makeStoryboard, tag } from '../shell/flowkit';
import { SETUP_MS, backendDown, budget, shot } from './helpers';

test.describe.configure({ timeout: SETUP_MS });
// 하나의 동작이 막히면 전체 시간(수 분)을 기다리지 않고 바로 실패하게
test.use({ actionTimeout: 45_000 });

/** 보드 DSS-01(용산 AI Ready 오피스) — 비교 기준 칩이 보드(사이니지 6 · LED 1 · 협업 디스플레이 1 · 비디오월 1 · IoT · 솔루션 3)와 같게 */
const BOARD_DSS = {
  industry: { value: '오피스 · 업무시설', by: 'manual', basis: null },
  spaces: [
    { name: '로비', by: 'manual', products: [{ name: 'The Wall IAB 146"', kind: 'product', ref: null, qty: '1식', by: 'manual' }, { name: 'Smart Signage QM55C', kind: 'product', ref: null, qty: '2대', by: 'manual' }] },
    { name: '라운지', by: 'manual', products: [{ name: 'Smart Signage QB43C', kind: 'product', ref: null, qty: '2대', by: 'manual' }] },
    { name: '회의실', by: 'manual', products: [{ name: 'Flip Pro WA75D', kind: 'product', ref: null, qty: '4대', by: 'manual' }, { name: 'Smart Signage QB55C', kind: 'product', ref: null, qty: '4대', by: 'manual' }] },
    { name: '중앙관제실', by: 'manual', products: [{ name: '비디오월 VM55B', kind: 'product', ref: null, qty: '9대', by: 'manual' }] },
    { name: '공용공간', by: 'manual', products: [{ name: 'Smart Signage QM43C', kind: 'product', ref: null, qty: '3대', by: 'manual' }, { name: 'Smart Signage QH55C', kind: 'product', ref: null, qty: '2대', by: 'manual' }] },
    { name: '엘리베이터 홀', by: 'manual', products: [{ name: 'Smart Signage OM46B', kind: 'product', ref: null, qty: '2대', by: 'manual' }] },
  ],
  solutions: [
    { name: 'MagicINFO', ref: 'kb:solution:sol_magicinfo', by: 'manual', links: [], why: null },
    { name: 'SmartThings Pro', ref: 'kb:solution:sol_smartthings_pro', by: 'manual', links: [], why: null },
    { name: 'b.IoT', ref: 'kb:solution:sol_biot', by: 'manual', links: [], why: null },
  ],
  counts: { spaces: 6, products: 9, solutions: 3 },
};

/** 입력칸 여러 개의 값 */
const vals = (l: Locator) => l.evaluateAll((els) => els.map((e) => (e as HTMLInputElement | HTMLTextAreaElement).value));
const w = async (l: Locator) => Math.round((await l.boundingBox())!.width);
const h = async (l: Locator) => Math.round((await l.boundingBox())!.height);

async function widths(page: Page) {
  return { flow: await w(page.locator('.wm-flow')), body: await w(page.locator('.caf-body')), left: await w(page.locator('.caf-left')),
    detail: await w(page.locator('.caf-detail, .caf-nosel').first()) };
}

const CF = (id: string) => `/api/competitor/v1/ca-flows/${id}`;
async function getDoc(request: APIRequestContext, id: string) {
  for (let i = 0; ; i++) {
    const r = await request.get(CF(id));
    if (r.ok()) return r.json();
    if (i >= 2) throw new Error(`GET ${id} → ${r.status()}`);
    await new Promise((res) => setTimeout(res, 300));
  }
}
const comp = (d: any, name: string) => d.competitors.find((c: any) => c.name === name);

type Dims = Record<string, { verdict: string; note: string }>;
const D = (spec: [string, string], price: [string, string], cases: [string, string], esg: [string, string], brand: [string, string]): Dims =>
  Object.fromEntries((['spec', 'price', 'cases', 'esg', 'brand'] as const).map((k, i) => [k, { verdict: [spec, price, cases, esg, brand][i][0], note: [spec, price, cases, esg, brand][i][1] }]));

/** 판정 알약(보드 c-pill · aria-haspopup=listbox) */
const pill = (page: Page, ours: string, dim: string) => page.getByRole('button', { name: new RegExp(`^${ours.replace(/[.*+?^${}()|[\]\\"]/g, '\\$&')} ${dim} 판정 · `) });
async function pickVerdict(page: Page, ours: string, dim: string, v: string) {
  await pill(page, ours, dim).click();
  await page.getByRole('listbox', { name: `${ours} ${dim} 판정` }).getByRole('option', { name: v, exact: true }).click();
  await expect(pill(page, ours, dim)).toHaveText(v);
}
async function typeIn(page: Page, scope: Locator, label: string, text: string) {
  const box = scope.getByRole('textbox', { name: label, exact: true });
  await box.fill(text);
  await box.press('Enter');
}

test('CA v63 — 목록 · 팝업 · 빈 최종본 · 바로 고치기 · AI 후보 · 저장 · 고친 곳 · 되돌리기 · v2 · 비교표', async ({ page, request }) => {
  budget(360_000);
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
  await page.setViewportSize({ width: 1440, height: 900 });

  // 사전 작업: Storyboard(rq → dss). DSS 는 보드 DSS-01 값으로 바꿔 넣는다(비교 기준 칩 · 비교 쌍이 보드와 같게)
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });
  const dssRef = `DSS-${tag()}`;
  const put = await request.put(`/api/storyboard/v1/flows/${sb.id}/stages/dss`, {
    headers: internalHeaders('dss'),
    data: { ref: dssRef, ver: 1, value: BOARD_DSS, md: '- 업종: 오피스 · 업무시설 · 공간 6\n- 솔루션: MagicINFO · SmartThings Pro · b.IoT' },
  });
  expect(put.ok(), await put.text()).toBeTruthy();

  // CA0 — 목록(보드 List content=ca) → 「새 경쟁사 분석 만들기」 → 목록 위 팝업(보드 CA1 = Gate)
  await page.goto('/competitor');
  await expect(page.getByRole('heading', { name: '경쟁사 분석', exact: true })).toBeVisible();
  await page.getByRole('link', { name: /새 경쟁사 분석 만들기/ }).click();
  await expect(page).toHaveURL(/\/competitor\/new$/);
  const gate = page.getByRole('dialog', { name: '새 경쟁사 분석 만들기 · Storyboard 고르기' });
  await expect(gate).toBeVisible();
  await expect(gate.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '경쟁사 분석', exact: true })).toBeAttached();      // 뒤에는 목록이 그대로
  const radio = gate.getByRole('radio', { name: new RegExp(sb.name) });
  await radio.click();
  await expect(radio).toHaveAttribute('aria-checked', 'true');
  await page.mouse.move(10, 890);
  await shot(page, 'CA1');
  await gate.getByRole('button', { name: /이 Storyboard로 시작/ }).click();

  // CA2 — 새로 만들기(경쟁사 없음) = 같은 상세 한 장. 완료 · 단계 화면 없음
  await expect(page).toHaveURL(/\/competitor\/flow\/cflow_[0-9A-Za-z]+$/, { timeout: 20_000 });
  const fid = page.url().split('/').pop()!.split('?')[0];
  const head = page.locator('.cd-head');
  await expect(head.locator('.cd-h1')).toHaveText(`${sb.name} 경쟁사`);
  await expect(head.locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(head.locator('.cd-meta')).toHaveText(`새로 만드는 중 · 쓰는 대로 작성 중으로 남아요 · 저장하면 ${sb.id}에 연결돼요`);
  await expect(head.getByRole('button', { name: '저장', exact: true })).toBeVisible();
  await expect(page.locator('.caf-strip__b')).toHaveText(`비교 기준 · ${dssRef}`);
  await expect(page.locator('.caf-cat')).toHaveText(['사이니지 6', 'LED 1', '협업 디스플레이 1', '비디오월 1', 'IoT · 솔루션 3']);
  await expect(page.getByRole('tablist', { name: '보기' }).getByRole('tab')).toHaveText(['경쟁사별', '비교표']);
  await expect(page.getByRole('tab', { name: '경쟁사별' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('.caf-lhead')).toHaveText('경쟁사 0비교 쌍 0');
  await expect(page.locator('.caf-lempty')).toHaveText('아직 경쟁사가 없어요아래에 회사 이름을 넣거나 위의 AI 경쟁사 후보군 웹 탐색을 눌러요');
  await expect(page.locator('.caf-nosel')).toContainText('경쟁사를 고르면 여기서 바로 비교해요');
  await expect(page.locator('.wm-sbbar__chip')).toContainText(sb.name);
  await expect(page.getByText('저장하면 이 Storyboard에 연결돼요 · 사전 작업에서 골랐어요')).toBeVisible();
  // 보드 CA2: 본문 열 1180 → 본문 1100 · 목록 290 | 상세 1fr(1100 − 290 − 14 = 796) · 띠 48 · AI 버튼 36 · 보기 전환 34 · 칩 24+선 · 목록 머리 42 + 선 · 추가 입력 36
  expect(await widths(page)).toEqual({ flow: 1180, body: 1100, left: 290, detail: 796 });
  expect(await h(page.locator('.caf-strip'))).toBe(48);
  expect(await h(page.getByRole('button', { name: 'AI 경쟁사 후보군 웹 탐색' }))).toBe(36);
  expect(await h(page.locator('.caf-seg'))).toBe(34);
  expect(await h(page.locator('.caf-cat').first())).toBe(26);
  expect(await h(page.locator('.caf-lhead'))).toBe(43);
  expect(await h(page.locator('#ca-add'))).toBe(36);
  expect(await h(head.getByRole('button', { name: '저장', exact: true }))).toBe(42);
  await page.mouse.move(10, 890);
  await shot(page, 'CA2');
  // 경쟁사 없이 저장하면 알려만 준다(서버 422 NO_COMPETITORS → 토스트 · 그대로 새로 만들기)
  await head.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: '경쟁사를 하나 이상 목록에 넣어 주세요' })).toBeVisible();
  await expect(head.locator('.cd-ref')).toHaveText('새로 만들기');

  // 바로 입력 — 회사 이름 → 위키(웹 검색 요약에 근거가 있는 값만) · 겹치는 제품군의 DSS 제품으로 비교 쌍
  await page.getByLabel('경쟁사 추가').fill('경쟁사 A');
  await page.getByLabel('경쟁사 추가').press('Enter');
  const rowA = page.locator('.caf-row[data-cid="A"]');
  await expect(rowA).toContainText('경쟁사 A', { timeout: 20_000 });
  await expect(rowA.locator('.caf-tag')).toHaveText('직접');
  await expect(rowA.locator('.caf-card__meta')).toHaveText('전자 · 디스플레이 · 대기업');
  await expect(rowA.locator('.caf-card__why')).toContainText('사이니지 · LED 겹침 · 로비');
  await expect(page.getByLabel('경쟁사 추가')).toHaveValue('');
  await expect(head.locator('.cd-ref')).toHaveText('작성 중');
  await page.getByLabel('경쟁사 추가').fill('경쟁사 B');
  await page.getByLabel('경쟁사 추가').press('Enter');
  await expect(page.locator('.caf-row[data-cid="B"]')).toContainText('협업 디스플레이 겹침 · 회의실', { timeout: 20_000 });
  await rowA.locator('.caf-card').click();
  await expect(rowA.locator('.caf-card')).toHaveAttribute('aria-pressed', 'true');
  const det = page.locator('.caf-detail');
  await expect(det.locator('.caf-dname')).toContainText('경쟁사 A');
  await expect(det.locator('.caf-oneline')).toHaveText('전자 · 디스플레이 · 상업용 디스플레이 · LED 월 · 국내');
  await expect(det.getByRole('button', { name: '목록에서 빼기' })).toBeVisible();
  await expect(page.getByRole('tab', { name: '제안 기준 비교' })).toHaveAttribute('aria-selected', 'true');
  await expect(det.locator('.caf-ours')).toHaveText(['The Wall IAB 146"', 'Smart Signage QM55C']);
  await expect(det.getByRole('textbox', { name: 'The Wall IAB 146" 경쟁 제품' })).toHaveValue('[확인 필요]');
  expect(await h(det.locator('.caf-letter'))).toBe(40);
  expect(await h(page.getByRole('tab', { name: '제안 기준 비교' }))).toBe(36);
  expect(await w(det.locator('.caf-cmphead > span').first())).toBe(196);
  expect(await w(det.locator('.caf-cmphead > span').nth(1))).toBe(Math.round((796 - 2 - 36 - 4 - 196 - 30) / 5));   // (상세 − 선 − 좌우 18 − 2 − 196 − 간격 6×5) / 5
  expect(await h(rowA.locator('.caf-tag'))).toBe(20);

  // 판정 · 메모 · 경쟁 제품 · 공간 — 그 자리에서(고르기는 누르는 즉시 · 글은 칸을 떠날 때)
  await pickVerdict(page, 'The Wall IAB 146"', '스펙', '비슷');
  await typeIn(page, det, 'The Wall IAB 146" 스펙 메모', '해상도 동급 · 밝기 수치 확인');
  await pickVerdict(page, 'The Wall IAB 146"', '가격', '열위');
  await typeIn(page, det, 'The Wall IAB 146" 경쟁 제품', '올인원 LED 월 · 동급 크기');
  await typeIn(page, det, 'The Wall IAB 146" 공간', '로비 미디어월');
  // Esc 는 고치기를 거둔다
  const priceNote = det.getByRole('textbox', { name: 'The Wall IAB 146" 가격 메모' });
  await priceNote.fill('바뀌면 안 됨');
  await priceNote.press('Escape');
  await expect(priceNote).toHaveValue('');
  await expect.poll(async () => {
    const a = comp(await getDoc(request, fid), '경쟁사 A');
    const m = a.matches[0];
    return [m.space, m.theirs, m.dims.spec, m.dims.price];
  }, { timeout: 10_000 }).toEqual(['로비 미디어월', '올인원 LED 월 · 동급 크기', { verdict: 'similar', note: '해상도 동급 · 밝기 수치 확인' }, { verdict: 'ours-worse', note: '' }]);
  // 저장 전에는 고친 칸 표시가 없다(보드 CA_Draft)
  await expect(det.locator('.cd-in--chg, .caf-note--chg, .caf-ring')).toHaveCount(0);

  // 비교 쌍 더하기(우리 제품은 DSS 에서만)
  await det.getByRole('button', { name: '+ 비교 쌍 추가 · DSS 공간 제품 ↔ 경쟁 제품' }).click();
  const addPair = page.getByRole('group', { name: '비교 쌍 추가' });
  await addPair.getByLabel('우리 제품 · 솔루션(DSS)').selectOption('MagicINFO');
  await addPair.getByLabel('경쟁 제품').fill('자사 CMS');
  await addPair.getByRole('button', { name: '추가' }).click();
  await expect(det.locator('.caf-ours')).toHaveText(['The Wall IAB 146"', 'Smart Signage QM55C', 'MagicINFO']);
  await expect(addPair).toHaveCount(0);

  // 나머지 판정은 API 로 채운다(보드 CA_Draft · CA_View 예시 값 — 화면 대조용)
  let doc = await getDoc(request, fid);
  const A = comp(doc, '경쟁사 A');
  const fillA: Array<[string, string, string, Dims]> = [
    [A.matches[0].id, '로비 미디어월', '올인원 LED 월 · 동급 크기', D(['similar', '해상도 동급 · 밝기 수치 확인'], ['ours-worse', '가격 이점 없음 · 초기가 낮음 [견적 확인]'], ['ours-better', '국내 AI 오피스 로비 사례'], ['ours-better', '저전력 · 소재 인증 [확인]'], ['similar', '비슷'])],
    [A.matches[1].id, '로비 안내 사이니지', '55" 보급형 사이니지', D(['ours-better', '24/7 운영 등급 · 고휘도'], ['ours-worse', '단가 높음'], ['similar', '비슷'], ['similar', '비슷'], ['ours-better', 'B2B 사이니지 인지도'])],
    [A.matches[2].id, '콘텐츠 관리', '자사 CMS', D(['ours-better', '원격 일괄 배포 · 예약 · 공간 연동'], ['similar', '비슷'], ['ours-better', '대형 오피스 · 리테일 사례'], ['no-data', '자료 없음'], ['similar', '비슷'])],
  ];
  for (const [mid, space, theirs, dims] of fillA) {
    const r = await request.patch(`${CF(fid)}/competitors/A/matches/${mid}`, { data: { space, theirs, dims } });
    expect(r.ok(), await r.text()).toBeTruthy();
  }
  const B = comp(doc, '경쟁사 B');
  await request.patch(`${CF(fid)}/competitors/B/matches/${B.matches[0].id}`, { data: { space: '회의실 협업 보드', theirs: '75" 인터랙티브 보드',
    dims: D(['similar', '터치 · 판서 동급'], ['similar', '가격 비슷'], ['ours-worse', '회의실 단독 사례가 더 많음'], ['similar', '비슷'], ['similar', '비슷']) } });
  doc = await (await request.post(`${CF(fid)}/competitors/B/matches`, { data: { ours: 'Smart Signage QB55C', space: '회의실 화상 화면', theirs: '회의실 디스플레이' } })).json();
  await request.patch(`${CF(fid)}/competitors/B/matches/${comp(doc, '경쟁사 B').matches[1].id}`, {
    data: { dims: D(['similar', '비슷'], ['ours-better', '단가 낮음 [견적 확인]'], ['similar', '비슷'], ['no-data', '자료 없음'], ['ours-better', '인지도']) } });
  await page.reload();
  await expect.poll(() => vals(det.locator('.caf-theirs input'))).toEqual(['올인원 LED 월 · 동급 크기', '55" 보급형 사이니지', '자사 CMS']);
  await expect(det.locator('[data-dim="spec"] .caf-pill')).toHaveText(['비슷', '우위', '우위']);
  await expect(det.locator('[data-dim="esg"] .caf-pill').last()).toHaveText('자료 없음');
  await expect(page.locator('.caf-lhead')).toHaveText('경쟁사 2비교 쌍 5');
  await expect(head.locator('.cd-ref')).toHaveText('작성 중');
  await expect(head.locator('.cd-meta')).toContainText('작성 중 · 경쟁사 2 · 비교 쌍 5 · ');
  await expect(head.locator('.cd-meta')).toContainText(`자동 저장 · 저장하면 ${sb.id}에 연결돼요`);
  await page.mouse.move(10, 890);
  await shot(page, 'CA_Draft');

  // CA2_Info — 개요 · 선별 기준(기본 정보 6칸 · 자리표시는 주황 칸 · 선별 기준 · 확인 필요 · + 기준 추가)
  await page.getByRole('tab', { name: '개요 · 선별 기준' }).click();
  await expect(det.locator('.caf-mcell__k')).toHaveText(['본사', '규모', '임직원', '업종', '주력 사업', 'B2B 오피스']);
  await expect.poll(() => vals(det.locator('.caf-mcell input'))).toEqual(['국내', '대기업 · 매출 [위키 값]', '[위키 값]', '전자 · 디스플레이', '상업용 디스플레이 · LED 월', '국내 납품 다수']);
  await expect(det.locator('.caf-mcell input.caf-min--ph')).toHaveCount(2);
  await expect(det.locator('.caf-src')).toContainText('기본 정보 · 웹 검색 요약 기준');
  await expect(det.locator('.caf-src')).toContainText('[위키 값]은 원문에서 채워요');
  await expect(det.locator('.caf-hrow')).toHaveText('선별 기준왜 이 회사를 경쟁사로 봤는지');
  await expect(det.locator('.caf-crit__k')).toHaveText(['제품군', '공간', '고객 접점']);
  await expect(det.getByRole('textbox', { name: '고객 접점 선별 기준' })).toHaveValue('E 자산운용 거래 이력');
  await expect(det.locator('.caf-tbd:not(.caf-tbd--mark)')).toHaveText(['확인 필요']);
  expect(await w(det.locator('.caf-mcell').first())).toBe(Math.floor((796 - 2 - 36 - 16) / 3));
  expect(await h(det.getByRole('textbox', { name: '경쟁사 A 본사' }))).toBe(32);
  expect(await h(det.getByRole('textbox', { name: '고객 접점 선별 기준' }))).toBe(34);
  expect(await w(det.locator('.caf-crit__k').first())).toBe(84);
  await page.mouse.move(10, 890);
  await shot(page, 'CA2_Info');
  // 기본 정보 고치기(규모 = 규모 · 매출) · 확인 필요 풀기 → 다시 표시 · 기준 추가
  await typeIn(page, det, '경쟁사 A 규모', '대기업 · 매출 [위키 값]');
  await det.getByRole('button', { name: '고객 접점 확인 필요 · 눌러서 확인 끝내기' }).click();
  await expect(det.locator('.caf-tbd:not(.caf-tbd--mark)')).toHaveCount(0);
  await det.locator('.caf-crit').last().hover();
  await det.getByRole('button', { name: '고객 접점 확인 필요로 표시' }).click();
  await expect(det.locator('.caf-tbd:not(.caf-tbd--mark)')).toHaveText(['확인 필요']);
  await det.getByRole('button', { name: '+ 기준 추가' }).click();
  await det.getByRole('textbox', { name: '새 선별 기준 이름' }).fill('가격대');
  await typeIn(page, det, '새 선별 기준', '보급형 사이니지 단가가 비슷함');
  await expect(det.locator('.caf-crit__k')).toHaveText(['제품군', '공간', '고객 접점', '가격대']);
  await expect.poll(async () => {
    const a = comp(await getDoc(request, fid), '경쟁사 A');
    return [a.wiki.size, a.wiki.revenue, a.criteria.map((x: any) => [x.k, x.status])];
  }, { timeout: 10_000 }).toEqual(['대기업', '[위키 값]', [['제품군', 'ok'], ['공간', 'ok'], ['고객 접점', 'check'], ['가격대', 'check']]]);
  await request.patch(`${CF(fid)}/competitors/A`, { data: { criteria: (await getDoc(request, fid)).competitors[0].criteria.slice(0, 3) } });

  // CA2_Pc — 장단점 · 주장 포인트(줄 더하기 · 주장 축 고르기)
  await page.getByRole('tab', { name: '장단점 · 주장 포인트' }).click();
  await expect(det.locator('.caf-pcbox__h')).toHaveText(['경쟁사 장점 · 삼성 대비', '경쟁사 단점 · 삼성 대비']);
  await expect(det.locator('.caf-claims__h')).toHaveText('그래서 우리가 주장할 것');
  const addLine = async (box: 'pros' | 'cons', text: string) => {
    await det.locator(`.caf-pcbox--${box}`).getByRole('button', { name: '+ 추가' }).click();
    await typeIn(page, det, `경쟁사 A 새 ${box === 'pros' ? '장점' : '단점'}`, text);
    await expect(det.locator(`.caf-pcbox--${box} input`).last()).toHaveValue(text);
  };
  await addLine('pros', '초기 도입가가 낮음 [견적 확인]');
  await addLine('pros', '국내 유지보수 거점이 많음 [확인 필요]');
  await addLine('cons', '사이니지 · IoT · 관제가 따로 놀아 공간 통합이 약함');
  await addLine('cons', 'AI 오피스 레퍼런스가 적음');
  const claims: Array<[string, string]> = [
    ['통합', 'MagicINFO · SmartThings Pro · b.IoT 하나의 플랫폼으로 공간 7개를 묶음'],
    ['사례', '국내 AI 오피스 로비 도입사례로 RQ-01 ‘최초 AI Ready’ 뒷받침'],
    ['가격', '초기가는 높지만 원격 관리로 운영비 절감 — RQ-01'],
  ];
  for (const [i, [axis, text]] of claims.entries()) {
    await det.getByRole('button', { name: '+ 주장 추가' }).click();
    if (axis !== '통합') {
      await det.getByRole('button', { name: /^새 주장 축 · / }).click();
      await det.getByRole('listbox', { name: '새 주장 축' }).getByRole('option', { name: axis, exact: true }).click();
    }
    await typeIn(page, det, '새 주장', text);
    await expect(det.getByRole('button', { name: new RegExp(`^주장 ${i + 1} 축 · `) })).toHaveText(axis);
  }
  // 있는 주장의 축은 고르기로 바꾼다(바꿨다가 되돌림)
  for (const axis of ['ESG', '가격']) {
    await det.getByRole('button', { name: /^주장 3 축 · / }).click();
    await det.getByRole('listbox', { name: '주장 3 축' }).getByRole('option', { name: axis, exact: true }).click();
    await expect(det.getByRole('button', { name: /^주장 3 축 · / })).toHaveText(axis);
  }
  await expect.poll(() => vals(det.locator('.caf-pcbox--pros input'))).toEqual(['초기 도입가가 낮음 [견적 확인]', '국내 유지보수 거점이 많음 [확인 필요]']);
  await expect.poll(async () => {
    const a = comp(await getDoc(request, fid), '경쟁사 A');
    return [a.pros.length, a.cons.length, a.claims.map((c: any) => [c.axis, c.supports])];
  }, { timeout: 10_000 }).toEqual([2, 2, [['통합', null], ['사례', null], ['가격', 'RQ-01']]]);
  expect(await w(det.locator('.caf-pcbox').first())).toBe((796 - 2 - 36 - 10) / 2);
  expect(await h(det.getByRole('button', { name: /^주장 1 축 · / }))).toBe(26);
  await page.mouse.move(10, 890);
  await shot(page, 'CA2_Pc');

  // CA2_AI — AI 경쟁사 후보군 웹 탐색(점선 후보 · 근거 출처) → 첫 후보를 고른다
  await page.getByRole('tab', { name: '제안 기준 비교' }).click();
  await page.getByRole('button', { name: 'AI 경쟁사 후보군 웹 탐색' }).click();
  const rowC = page.locator('.caf-row[data-cid="C"]');
  await expect(rowC).toContainText('경쟁사 C', { timeout: 20_000 });
  await expect(page.locator('.caf-row--cand')).toHaveCount(3);
  await expect(page.locator('.caf-row--cand .caf-tag')).toHaveText(['AI 후보', 'AI 후보', 'AI 후보']);
  await expect(page.locator('.caf-row--cand .caf-addcand')).toHaveText(['추가', '추가', '추가']);
  await expect(rowC.locator('.caf-card')).toHaveAttribute('aria-pressed', 'true');
  await expect(rowC.locator('.caf-card__meta')).toHaveText('산업용 디스플레이 · 관제 · 중견');
  await expect(det).toHaveClass(/caf-detail--cand/);
  await expect(page.locator('.caf-lhead')).toHaveText('경쟁사 2점선은 AI 후보 · 추가해야 들어가요');     // 후보는 아직 목록에 들지 않는다
  {   // 보드 CA2_AI: 「목록에 추가」 h34 · 상세 머리 오른쪽 안쪽 14 + 점선
    const btn = (await det.getByRole('button', { name: '목록에 추가', exact: true }).boundingBox())!;
    const box = (await det.boundingBox())!;
    expect(Math.round(btn.height)).toBe(34);
    expect(Math.round(box.x + box.width - (btn.x + btn.width))).toBe(15);   // 1.5px 점선은 DPR 1 에서 1px 로 그려진다
  }
  await expect(det.locator('.caf-ours')).toHaveText(['비디오월 VM55B', 'b.IoT']);
  expect(await h(rowC.locator('.caf-tag'))).toBe(22);
  expect(await widths(page)).toEqual({ flow: 1180, body: 1100, left: 290, detail: 796 });
  await page.mouse.move(10, 890);
  await shot(page, 'CA2_AI');

  // 추가(상세 「목록에 추가」 · 목록 줄 「추가」) — 5곳 · 비교 쌍 9(보드 CA_View)
  await det.getByRole('button', { name: '목록에 추가', exact: true }).click();
  await expect(rowC.locator('.caf-tag')).toHaveText('AI 웹 탐색 · 추가');
  await expect(det).not.toHaveClass(/caf-detail--cand/);
  await page.getByRole('button', { name: '경쟁사 D 목록에 추가' }).click();
  await expect(page.locator('.caf-row[data-cid="D"] .caf-tag')).toHaveText('AI 웹 탐색 · 추가');
  await page.getByRole('button', { name: '경쟁사 E 목록에 추가' }).click();
  await expect(page.locator('.caf-row--cand')).toHaveCount(0);
  await expect(page.locator('.caf-lhead')).toHaveText('경쟁사 5비교 쌍 9');

  // 저장 → 그 자리에서 저장됨(문서 다시 읽기 · 토스트) — 완료 화면 없음
  await head.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: /v1 저장 · 경쟁사 5/ })).toBeVisible({ timeout: 20_000 });
  doc = await getDoc(request, fid);
  expect([doc.status, doc.ver, doc.changes]).toEqual(['done', 1, 0]);
  await expect(page).toHaveURL(new RegExp(`/competitor/flow/${fid}$`));
  await expect(head.locator('.cd-ref')).toHaveText(`${doc.code} v1`);
  await expect(head.locator('.cd-meta')).toContainText(' 저장 · 경쟁사 5 · 비교 쌍 9');
  await expect(head.locator('.cd-hint')).toHaveText('눌러서 바로 고쳐요');
  await expect(head.getByRole('button', { name: /flow\.json/ })).toBeVisible();
  await expect(head.getByRole('button', { name: /^저장/ })).toHaveCount(0);
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const sca = flow.stages.ca;
  expect([sca.ref, sca.ver]).toEqual([doc.code, 1]);
  expect(sca.basis).toEqual({ from: dssRef, categories: ['사이니지', 'LED', '협업 디스플레이', '비디오월', 'IoT · 솔루션'] });
  expect(sca.competitors.map((c: any) => [c.id, c.name, c.by])).toEqual([['A', '경쟁사 A', 'manual'], ['B', '경쟁사 B', 'manual'], ['C', '경쟁사 C', 'ai-web'], ['D', '경쟁사 D', 'ai-web'], ['E', '경쟁사 E', 'ai-web']]);
  expect(sca.competitors[0].matches[0]).toEqual({ space: '로비 미디어월', ours: 'The Wall IAB 146"', theirs: '올인원 LED 월 · 동급 크기', dims: fillA[0][3] });
  expect(sca.competitors[0].claims[2]).toEqual({ axis: '가격', text: '초기가는 높지만 원격 관리로 운영비 절감', supports: 'RQ-01' });
  expect(sca.counts).toMatchObject({ competitors: 5, matches: 9, verdicts: { oursBetter: 14, similar: 21, oursWorse: 6, noData: 4 } });
  expect(flow.cells.find((c: any) => c.key === 'ca')).toMatchObject({ state: 'done', ref: doc.code, route: `/competitor/flow/${fid}` });

  // CA_View — 저장됨 · 경쟁사 A · 제안 기준 비교
  await rowA.locator('.caf-card').click();
  await expect(det.locator('.caf-dname')).toContainText('경쟁사 A');
  await page.mouse.move(10, 890);
  await shot(page, 'CA_View');

  // 한 칸 고치기 → 「고친 곳 1」 · 고리 → 되돌리기
  await pickVerdict(page, 'The Wall IAB 146"', '가격', '비슷');
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 1');
  await expect(head.locator('.cd-ref')).toHaveText(`${doc.code} v1 · 고치는 중`);
  await expect(head.locator('.cd-meta')).toHaveText(`${doc.code} v1 고치는 중 · 저장하면 v2 · ${sb.id}에 반영돼요`);
  await expect(head.getByRole('button', { name: '저장 · v2' })).toBeVisible();
  await expect(pill(page, 'The Wall IAB 146"', '가격')).toHaveClass(/caf-ring/);
  await head.getByRole('button', { name: '되돌리기' }).click();
  await expect(page.getByRole('status').filter({ hasText: `${doc.code} v1로 되돌렸어요` })).toBeVisible();
  await expect(head.locator('.cd-chg')).toHaveCount(0);
  await expect(head.locator('.cd-ref')).toHaveText(`${doc.code} v1`);
  await expect(pill(page, 'The Wall IAB 146"', '가격')).toHaveText('열위');
  await expect(det.locator('.caf-ring, .caf-note--chg, .cd-in--chg')).toHaveCount(0);
  expect((await getDoc(request, fid)).changes).toBe(0);

  // CA2_Edit — 판정 · 메모 고침 = 고친 곳 2(고리 · 파란 칸) → 저장 · v2
  await pickVerdict(page, 'The Wall IAB 146"', '가격', '비슷');
  await typeIn(page, det, 'The Wall IAB 146" 가격 메모', '초기가는 낮지만 운영비까지 보면 비슷 [견적 확인]');
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 2');
  await page.mouse.move(10, 890);
  await expect(det.getByRole('textbox', { name: 'The Wall IAB 146" 가격 메모' })).toHaveClass(/caf-note--chg/);
  await expect(det.locator('.caf-ring')).toHaveCount(1);
  // 보드 CA2_Edit: 고친 메모 상자 = 브랜드 테두리 · #f6f8fe
  await expect(det.getByRole('textbox', { name: 'The Wall IAB 146" 가격 메모' })).toHaveCSS('border-top-color', 'rgb(20, 40, 160)');
  await expect(det.getByRole('textbox', { name: 'The Wall IAB 146" 가격 메모' })).toHaveCSS('background-color', 'rgb(246, 248, 254)');
  await page.mouse.move(10, 890);
  await shot(page, 'CA2_Edit');
  await head.getByRole('button', { name: '저장 · v2' }).click();
  await expect(page.getByRole('status').filter({ hasText: /v2 저장 · 경쟁사 5/ })).toBeVisible({ timeout: 20_000 });
  await expect(head.locator('.cd-ref')).toHaveText(`${doc.code} v2`);
  await expect(head.locator('.cd-chg')).toHaveCount(0);
  await expect(det.locator('.caf-ring, .caf-note--chg')).toHaveCount(0);
  const flow2 = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  expect(flow2.stages.ca.ver).toBe(2);
  expect(flow2.stages.ca.competitors[0].matches[0].dims.price).toEqual({ verdict: 'similar', note: '초기가는 낮지만 운영비까지 보면 비슷 [견적 확인]' });

  // CA_Table — 비교표: 판정 합계 · 236 + 82×5 + 1fr · 행을 누르면 경쟁사별에서 그 경쟁사
  await page.getByRole('tab', { name: '비교표' }).click();
  const table = page.locator('.caf-table');
  await expect(table.locator('.caf-tally')).toHaveText('판정 합계우위14비슷22열위5자료 없음4행을 누르면 경쟁사별에서 바로 고쳐요');
  await expect(table.locator('.caf-thead > span')).toHaveText(['경쟁사 · 겹치는 공간', '스펙', '가격', '유관 사례', 'ESG', '브랜드 평판', '우리 주장 포인트']);
  await expect(table.locator('.caf-tline')).toHaveCount(5);
  const tA = table.locator('.caf-tline[data-cid="A"]');
  await expect(tA.locator('.caf-tname__w')).toHaveText('전자 · 디스플레이 · 대기업 · 국내');
  await expect(tA.locator('.caf-tname__s')).toHaveText('로비 · 라운지 · 회의실 · 공용공간 · 엘리베이터 홀 겹침');
  await expect(tA.locator('.caf-tcell .caf-chip')).toHaveText(['우위', '열위', '우위', '우위', '우위']);       // v2: 가격 열위 2 → 1
  await expect(tA.locator('.caf-tcell__n')).toHaveText(['2 / 3쌍', '1 / 3쌍', '2 / 3쌍', '1 / 3쌍', '1 / 3쌍']);
  await expect(tA.locator('.caf-tclaim')).toHaveCount(2);
  await expect(table.locator('.caf-tline[data-cid="C"] .caf-tag')).toHaveText('AI 웹 탐색');
  expect(await w(table.locator('.caf-thead > span').first())).toBe(236);
  expect(await w(table.locator('.caf-thead > span').nth(1))).toBe(82);
  expect(await w(table)).toBe(1100);
  expect(await h(table.locator('.caf-tally'))).toBe(41);
  await page.mouse.move(10, 890);
  await shot(page, 'CA_Table');
  await table.locator('.caf-tline[data-cid="C"]').click();
  await expect(page.getByRole('tab', { name: '경쟁사별' })).toHaveAttribute('aria-selected', 'true');
  await expect(det.locator('.caf-dname')).toContainText('경쟁사 C');

  // flow.json 팝업 · 목록 카드(코드 v2 · Storyboard 칩)
  await head.getByRole('button', { name: /flow\.json/ }).click();
  const dlg = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByText('"ca": {').first()).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(dlg).toHaveCount(0);
  await page.goto('/competitor');
  const card = page.locator('.fl-card').filter({ hasText: `${doc.code} v2` });
  await expect(card).toBeVisible();
  await expect(card.getByRole('button', { name: sb.name })).toBeVisible();
  await expect(card.locator('.fl-cardtitle')).toHaveAttribute('href', `/competitor/flow/${fid}`);
});

test('CA v63 — Storyboard 「만들기」(?sb=&auto=1) · 1920 폭 · AI 후보 없음 · 목록에서 빼기 · 예전 주소 · 이전 흐름 경로', async ({ page, request }) => {
  budget(150_000);
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makeStoryboard(request, { dss: true, name: `판교 스타트업 단지 ${tag()}` });

  // Storyboard 화면의 「만들기」 → 사전 작업 고르기를 건너뛰고 바로 빈 최종본(CF-07)
  await page.goto(`/competitor/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/competitor\/flow\/cflow_[0-9A-Za-z]+$/, { timeout: 20_000 });
  const fid = page.url().split('/').pop()!;
  await expect(page.locator('.caf-cat')).toHaveText(['사이니지 3', 'LED 1', '협업 디스플레이 1', '키오스크 1', 'IoT · 솔루션 2']);
  await expect(page.locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(page.getByText('경쟁사를 고르면 여기서 바로 비교해요')).toBeVisible();

  // 1920 폭에서도 본문 열은 1180 · 고정 칸 290 (UI-W-01 · UI-W-04)
  await page.setViewportSize({ width: 1920, height: 1080 });
  expect(await widths(page)).toEqual({ flow: 1180, body: 1100, left: 290, detail: 796 });
  await page.setViewportSize({ width: 1440, height: 900 });

  // AI 가 근거 있는 후보를 못 찾으면 알려만 준다(지어내지 않음)
  await page.route('**/api/competitor/v1/ca-flows/*:candidates', async (r) => {
    const id = /ca-flows\/([^/:]+):candidates/.exec(r.request().url())![1];
    const flow = await (await request.get(CF(id))).json();
    await r.fulfill({ json: { flow, added: 0, mode: 'none', reason: '지금은 AI 웹 탐색을 쓸 수 없어요 · 경쟁사를 직접 추가해 주세요.' } });
  });
  await page.getByRole('button', { name: 'AI 경쟁사 후보군 웹 탐색' }).click();
  await expect(page.getByText('지금은 AI 웹 탐색을 쓸 수 없어요 · 경쟁사를 직접 추가해 주세요.')).toBeVisible();
  await expect(page.locator('.caf-row')).toHaveCount(0);

  // 위키에 없는 회사 → 기본 정보는 모두 자리표시 · 비교 쌍 없음 → 「+ 비교 쌍 추가」 · 목록에서 빼기는 묻는다
  await page.getByLabel('경쟁사 추가').fill('모르는 회사');
  await page.getByLabel('경쟁사 추가').press('Enter');
  const det = page.locator('.caf-detail');
  await expect(det.locator('.caf-dname')).toContainText('모르는 회사', { timeout: 20_000 });
  await expect(det.getByText('비교 쌍이 없어요', { exact: false })).toBeVisible();
  await det.getByRole('button', { name: /^\+ 비교 쌍 추가/ }).click();
  await page.getByRole('group', { name: '비교 쌍 추가' }).getByLabel('우리 제품 · 솔루션(DSS)').selectOption('삼성 키오스크');
  await page.getByRole('group', { name: '비교 쌍 추가' }).getByRole('button', { name: '추가' }).click();
  await expect(det.locator('.caf-ours')).toHaveText(['삼성 키오스크']);
  await expect.poll(() => vals(det.locator('.caf-theirs input'))).toEqual(['[확인 필요]']);
  await expect.poll(() => vals(det.locator('.caf-pair__l > input'))).toEqual(['로비']);
  // 예전 주소(?tab=info)로 와도 같은 상세
  await page.goto(`/competitor/flow/${fid}?tab=info`);
  await expect(page.locator('.cd-ref')).toHaveText('작성 중');
  await page.getByRole('tab', { name: '개요 · 선별 기준' }).click();
  await expect.poll(() => vals(det.locator('.caf-mcell input'))).toEqual(['[확인 필요]', '[확인 필요] · 매출 [위키 값]', '[위키 값]', '[확인 필요]', '[확인 필요]', '[확인 필요]']);
  await det.getByRole('button', { name: '목록에서 빼기' }).click();
  const confirmDlg = page.getByRole('dialog', { name: /모르는 회사를 목록에서 뺄까요/ });
  await expect(confirmDlg).toBeVisible();
  await confirmDlg.getByRole('button', { name: '빼기' }).click();
  await expect(page.locator('.caf-row')).toHaveCount(0);
  await expect(page.locator('.cd-ref')).toHaveText('새로 만들기');

  // 이전 흐름: 정의서 진입(?input=requirements)은 이전 넣기 화면으로 · 이전 목록은 /competitor/legacy
  await page.goto('/competitor/new?input=requirements');
  await expect(page).toHaveURL(/\/competitor\/legacy\/new\?input=requirements$/);
  await page.goto('/competitor/legacy');
  await expect(page.getByRole('heading', { name: '경쟁사 분석 작업' })).toBeVisible();
  await expect(page.getByRole('link', { name: '새 분석' })).toHaveAttribute('href', '/competitor/legacy/new');
});
