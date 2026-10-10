/**
 * 경쟁사 분석 새 흐름(2026-10-08 보드 webapp1 CA0 · CA1 · CA2 · CA2_AI · CA2_Info · CA2_Pc · CA_Done · CA_DoneJson) — 실제 스택(mock 모델 · mocks/ai-tools/ca.flow_*.json).
 * Storyboard(rq → dss, API) → 목록 → Gate → CA2(직접 추가 · 판정 · 메모 · 비교 쌍 · AI 후보 웹 탐색 → 수락 · 빼기 · 탭 3 · 장단점 · 주장) → 저장 → 완료 + 전체 JSON(허브 stages.ca).
 * 보드 고정 칸(목록 290 · 본문 1180 → 상세 796 · 비교 첫 칸 200)을 숫자로 재고, 화면을 __screens__/<보드>-new.png 로 남긴다.
 * 실행: make e2e-feature SERVICE=competitor (1 worker) · 이 파일만: … npx playwright test e2e/competitor/ca-flow.spec.ts --workers=1
 */
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { internalHeaders, makeStoryboard, tag } from '../shell/flowkit';
import { SETUP_MS, backendDown, budget, shot } from './helpers';

test.describe.configure({ timeout: SETUP_MS });

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

const w = async (l: Locator) => Math.round((await l.boundingBox())!.width);
const h = async (l: Locator) => Math.round((await l.boundingBox())!.height);

async function widths(page: Page) {
  return { flow: await w(page.locator('.wm-flow')), left: await w(page.locator('.caf-left')), detail: await w(page.locator('.caf-detail')) };
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

test('CA 새 흐름 — 목록 · Gate · 직접 추가 · 비교 판정 · AI 후보 웹 탐색 · 탭 3 · 저장 · 완료(stages.ca)', async ({ page, request }) => {
  budget(300_000);
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

  // CA0 — 목록(보드 List content=ca)
  await page.goto('/competitor');
  await expect(page.getByRole('heading', { name: '경쟁사 분석', exact: true })).toBeVisible();
  await expect(page.getByText('Storyboard의 제품 · 공간을 기준으로 B2B 경쟁사를 리스트업해요.')).toBeVisible();
  await expect(page.getByText('사전 작업 · 최소 DSS까지 된 Storyboard')).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'CA0-new');
  await page.getByRole('link', { name: '새 경쟁사 분석' }).first().click();

  // CA1 — 사전 작업 Storyboard 고르기(보드 Gate content=ca)
  await expect(page).toHaveURL(/\/competitor\/new$/);
  await expect(page.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  await expect(page.getByText('최소 DSS까지 완료된 Storyboard이 있어야 시작할 수 있어요.', { exact: false })).toBeVisible();
  const radio = page.getByRole('radio', { name: new RegExp(sb.name) });
  await radio.click();
  await expect(radio).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByText(`${sb.name}에 경쟁사 분석이 연결돼요`)).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'CA1-new');
  await page.getByRole('button', { name: /이 Storyboard로 시작/ }).click();

  // CA2 — 비어 있는 새 경쟁사 분석
  await expect(page).toHaveURL(/\/competitor\/flow\/cflow_[0-9A-Za-z]+$/, { timeout: 20_000 });
  const fid = page.url().split('/').pop()!.split('?')[0];
  await expect(page.getByRole('heading', { name: '경쟁사를 리스트업하고 우리 제안과 비교해요' })).toBeVisible();
  await expect(page.locator('.caf-basis > b')).toHaveText(`비교 기준 · ${dssRef}`);
  await expect(page.locator('.caf-cat')).toHaveText(['사이니지 6', 'LED 1', '협업 디스플레이 1', '비디오월 1', 'IoT · 솔루션 3']);
  await expect(page.locator('.wm-sbbar__chip')).toContainText(sb.name);
  await expect(page.getByText('Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨')).toBeVisible();
  await expect(page.locator('.caf-lhead')).toHaveText('경쟁사 0점선은 AI 후보');
  await expect(page.getByText('경쟁사를 하나 이상 목록에 넣어 주세요')).toBeVisible();
  await expect(page.getByRole('button', { name: '저장', exact: true })).toBeDisabled();
  await expect(page.getByRole('link', { name: 'Storyboard', exact: true })).toHaveAttribute('href', `/storyboard/flow/${sb.id}`);
  // 보드 CA2: 본문 열 1180 · 목록 290 | 상세 1fr(1180 − 80 − 290 − 14 = 796) · AI 버튼 38 · 목록 머리 42 + 선 · 추가 입력 36 · 저장 48
  expect(await widths(page)).toEqual({ flow: 1180, left: 290, detail: 796 });
  expect(await h(page.getByRole('button', { name: 'AI 경쟁사 후보군 웹 탐색' }))).toBe(38);
  expect(await h(page.locator('.caf-lhead'))).toBe(43);
  expect(await h(page.locator('#ca-add'))).toBe(36);
  expect(await h(page.getByRole('button', { name: '저장', exact: true }))).toBe(48);
  expect(await h(page.locator('.caf-cat').first())).toBe(24);
  await page.mouse.move(10, 890);
  await shot(page, 'CA2-empty-new');

  // 직접 추가 — 회사 이름 → 위키(웹 검색 요약에 근거가 있는 값만) · 겹치는 제품군의 DSS 제품으로 비교 쌍
  await page.getByLabel('경쟁사 추가').fill('경쟁사 A');
  await page.getByLabel('경쟁사 추가').press('Enter');
  const rowA = page.locator('.caf-row[data-cid="A"]');
  await expect(rowA).toContainText('경쟁사 A', { timeout: 20_000 });
  await expect(rowA.locator('.caf-tag')).toHaveText('직접');
  await expect(rowA.locator('.caf-card__meta')).toHaveText('전자 · 디스플레이 · 대기업');
  await expect(rowA.locator('.caf-card__why')).toContainText('사이니지 · LED 겹침 · 로비');
  await expect(page.getByLabel('경쟁사 추가')).toHaveValue('');
  await page.getByLabel('경쟁사 추가').fill('경쟁사 B');
  await page.getByLabel('경쟁사 추가').press('Enter');
  await expect(page.locator('.caf-row[data-cid="B"]')).toContainText('협업 디스플레이 겹침 · 회의실', { timeout: 20_000 });
  await rowA.locator('.caf-card').click();
  await expect(rowA.locator('.caf-card')).toHaveAttribute('aria-pressed', 'true');
  const det = page.locator('.caf-detail');
  await expect(det.locator('.caf-dname')).toContainText('경쟁사 A');
  await expect(det.locator('.caf-oneline')).toHaveText('전자 · 디스플레이 · 상업용 디스플레이 · LED 월 · 국내');
  await expect(page.getByRole('tab', { name: '제안 기준 비교' })).toHaveAttribute('aria-selected', 'true');
  await expect(det.locator('.caf-ours')).toHaveText(['The Wall IAB 146"', 'Smart Signage QM55C']);
  await expect(det.locator('.caf-theirs').first()).toHaveText('↔ [확인 필요]');
  expect(await h(det.locator('.caf-letter'))).toBe(40);
  expect(await h(page.getByRole('tab', { name: '제안 기준 비교' }))).toBe(36);
  expect(await w(det.locator('.caf-cmphead > span').first())).toBe(200);
  expect(await h(rowA.locator('.caf-tag'))).toBe(20);

  // 판정 · 메모 · 경쟁 제품 · 공간(눌러서 고치기)
  await page.getByRole('button', { name: /^The Wall IAB 146" 스펙 판정 자료 없음/ }).click();
  await page.getByRole('menu', { name: 'The Wall IAB 146" 스펙 판정' }).getByRole('menuitemradio', { name: '비슷' }).click();
  await expect(page.getByRole('button', { name: /^The Wall IAB 146" 스펙 판정/ })).toHaveText('비슷');
  await page.getByRole('button', { name: 'The Wall IAB 146" 스펙 메모 고치기' }).click();
  await page.getByRole('textbox', { name: 'The Wall IAB 146" 스펙 메모' }).fill('해상도 동급 · 밝기 수치 확인');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: 'The Wall IAB 146" 스펙 메모 고치기' })).toHaveText('해상도 동급 · 밝기 수치 확인');
  await page.getByRole('button', { name: /^The Wall IAB 146" 가격 판정/ }).click();
  await page.getByRole('menuitemradio', { name: '열위' }).click();
  await expect(page.getByRole('button', { name: /^The Wall IAB 146" 가격 판정/ })).toHaveText('열위');
  await page.getByRole('button', { name: 'The Wall IAB 146" 경쟁 제품 고치기' }).click();
  await page.getByRole('textbox', { name: 'The Wall IAB 146" 경쟁 제품' }).fill('올인원 LED 월 · 동급 크기');
  await page.keyboard.press('Enter');
  await expect(det.locator('.caf-theirs').first()).toHaveText('↔ 올인원 LED 월 · 동급 크기');
  await page.getByRole('button', { name: 'The Wall IAB 146" 공간 고치기' }).click();
  await page.getByRole('textbox', { name: 'The Wall IAB 146" 공간' }).fill('로비 미디어월');
  await page.keyboard.press('Enter');
  await expect(det.locator('.caf-where').first()).toHaveText('로비 미디어월');
  // Esc 는 고치기를 거둔다
  await page.getByRole('button', { name: 'The Wall IAB 146" 가격 메모 고치기' }).click();
  await page.getByRole('textbox', { name: 'The Wall IAB 146" 가격 메모' }).fill('바뀌면 안 됨');
  await page.keyboard.press('Escape');
  await expect.poll(async () => {
    const a = comp(await getDoc(request, fid), '경쟁사 A');
    const m = a.matches[0];
    return [m.space, m.theirs, m.dims.spec, m.dims.price];
  }, { timeout: 10_000 }).toEqual(['로비 미디어월', '올인원 LED 월 · 동급 크기', { verdict: 'similar', note: '해상도 동급 · 밝기 수치 확인' }, { verdict: 'ours-worse', note: '' }]);

  // 비교 쌍 더하기(우리 제품은 DSS 에서만)
  await page.getByRole('button', { name: '+ 비교 쌍' }).click();
  const addPair = page.getByRole('group', { name: '비교 쌍 추가' });
  await addPair.getByLabel('우리 제품 · 솔루션(DSS)').selectOption('MagicINFO');
  await addPair.getByLabel('경쟁 제품').fill('자사 CMS');
  await addPair.getByRole('button', { name: '추가' }).click();
  await expect(det.locator('.caf-ours')).toHaveText(['The Wall IAB 146"', 'Smart Signage QM55C', 'MagicINFO']);
  await expect(addPair).toHaveCount(0);

  // 나머지 판정은 API 로 채운다(보드 CA2 예시 값 — 화면 대조용)
  let doc = await getDoc(request, fid);
  const A = comp(doc, '경쟁사 A');
  const fill: Array<[string, string, string, Dims]> = [
    [A.matches[0].id, '로비 미디어월', '올인원 LED 월 · 동급 크기', D(['similar', '해상도 동급 · 밝기 수치 확인'], ['ours-worse', '가격 이점 없음 · 초기가 낮음 [견적 확인]'], ['ours-better', '국내 AI 오피스 로비 사례'], ['ours-better', '저전력 · 소재 인증 [확인]'], ['similar', '비슷'])],
    [A.matches[1].id, '로비 안내 사이니지', '55" 보급형 사이니지', D(['ours-better', '24/7 운영 등급 · 고휘도'], ['ours-worse', '단가 높음'], ['similar', '비슷'], ['similar', '비슷'], ['ours-better', 'B2B 사이니지 인지도'])],
    [A.matches[2].id, '콘텐츠 관리', '자사 CMS', D(['ours-better', '원격 일괄 배포 · 예약 · 공간 연동'], ['similar', '비슷'], ['ours-better', '대형 오피스 · 리테일 사례'], ['no-data', '자료 없음'], ['similar', '비슷'])],
  ];
  for (const [mid, space, theirs, dims] of fill) {
    const r = await request.patch(`${CF(fid)}/competitors/A/matches/${mid}`, { data: { space, theirs, dims } });
    expect(r.ok(), await r.text()).toBeTruthy();
  }
  const B = comp(doc, '경쟁사 B');
  await request.patch(`${CF(fid)}/competitors/B/matches/${B.matches[0].id}`, { data: { space: '회의실 협업 보드', theirs: '75" 인터랙티브 보드',
    dims: D(['similar', '터치 · 판서 동급'], ['similar', '가격 비슷'], ['ours-worse', '회의실 단독 사례가 더 많음'], ['similar', '비슷'], ['similar', '비슷']) } });
  await page.reload();
  await expect(det.locator('.caf-theirs')).toHaveText(['↔ 올인원 LED 월 · 동급 크기', '↔ 55" 보급형 사이니지', '↔ 자사 CMS']);
  await expect(det.locator('[data-dim="spec"] .caf-pill')).toHaveText(['비슷', '우위', '우위']);
  await expect(det.locator('[data-dim="esg"] .caf-pill').last()).toHaveText('자료 없음');
  await expect(page.locator('.wm-flow__summary')).toHaveText('경쟁사 2 · 비교 쌍 4');
  await expect(page.locator('.caf-lhead')).toHaveText('경쟁사 2점선은 AI 후보');
  await page.mouse.move(10, 890);
  await shot(page, 'CA2-new');

  // CA2_AI — AI 경쟁사 후보군 웹 탐색(점선 후보 · 근거 출처) → 첫 후보를 고른다
  await page.getByRole('button', { name: 'AI 경쟁사 후보군 웹 탐색' }).click();
  const rowC = page.locator('.caf-row[data-cid="C"]');
  await expect(rowC).toContainText('경쟁사 C', { timeout: 20_000 });
  await expect(page.locator('.caf-row--cand')).toHaveCount(3);
  await expect(page.locator('.caf-row--cand .caf-tag')).toHaveText(['AI 후보', 'AI 후보', 'AI 후보']);
  await expect(rowC.locator('.caf-card')).toHaveAttribute('aria-pressed', 'true');
  await expect(rowC.locator('.caf-card__meta')).toHaveText('산업용 디스플레이 · 관제 · 중견');
  await expect(det).toHaveClass(/wm-flow__panel--dashed/);
  await expect(det.getByRole('button', { name: '목록에 추가', exact: true })).toBeVisible();
  {   // 보드 CA2_AI: 「목록에 추가」 h34 · 상세 머리 오른쪽 안쪽 16 + 점선(빼기 단추가 자리를 차지하지 않는다)
    const btn = (await det.getByRole('button', { name: '목록에 추가', exact: true }).boundingBox())!;
    const box = (await det.boundingBox())!;
    expect(Math.round(btn.height)).toBe(34);
    expect(Math.round(box.x + box.width - (btn.x + btn.width))).toBe(17);   // 1.5px 점선은 DPR 1 에서 1px 로 그려진다
  }
  await expect(det.locator('.caf-ours')).toHaveText(['비디오월 VM55B', 'b.IoT']);
  await expect(page.locator('.caf-lhead')).toHaveText('경쟁사 2점선은 AI 후보');      // 후보는 아직 목록에 들지 않는다
  expect(await h(rowC.locator('.caf-tag'))).toBe(22);
  expect(await widths(page)).toEqual({ flow: 1180, left: 290, detail: 796 });
  await page.mouse.move(10, 890);
  await shot(page, 'CA2_AI-new');

  // 수락(상세 「목록에 추가」) · 빼기(줄에 올렸을 때 보이는 × — 후보는 묻지 않고 뺀다)
  await det.getByRole('button', { name: '목록에 추가', exact: true }).click();
  await expect(rowC.locator('.caf-tag')).toHaveText('AI 웹 탐색 · 추가');
  await expect(det).not.toHaveClass(/wm-flow__panel--dashed/);
  await expect(page.locator('.caf-lhead')).toHaveText('경쟁사 3점선은 AI 후보');
  await page.locator('.caf-row[data-cid="E"] .caf-card').click();
  await expect(det.locator('.caf-dname')).toContainText('경쟁사 E');
  await page.locator('.caf-row[data-cid="E"]').hover();
  await page.getByRole('button', { name: '경쟁사 E 빼기' }).click();
  await expect(page.locator('.caf-row[data-cid="E"]')).toHaveCount(0);
  await expect(page.locator('.caf-row--cand')).toHaveCount(1);                     // 경쟁사 D 는 점선 그대로 → 저장에 안 들어간다

  // CA2_Info — 개요 · 선별 기준(기본 정보 6칸 · 자리표시는 주황 · 선별 기준 · 확인 필요)
  await rowA.locator('.caf-card').click();
  await page.getByRole('tab', { name: '개요 · 선별 기준' }).click();
  await expect(page).toHaveURL(/\?tab=info$/);
  await expect(det.locator('.caf-mcell__k')).toHaveText(['본사', '규모', '임직원', '업종', '주력 사업', 'B2B 오피스']);
  await expect(det.locator('.caf-mcell__v')).toHaveText(['국내', '대기업 · 매출 [위키 값]', '[위키 값]', '전자 · 디스플레이', '상업용 디스플레이 · LED 월', '국내 납품 다수']);
  await expect(det.locator('.caf-mcell__v.caf-ph')).toHaveCount(2);
  await expect(det.locator('.caf-src')).toHaveText('기본 정보 · 웹 검색 요약 기준 · 원문 URL [확인 필요]');
  await expect(det.locator('.caf-crit__k')).toHaveText(['제품군', '공간', '고객 접점']);
  await expect(det.locator('.caf-crit').last()).toContainText('E 자산운용 거래 이력');
  await expect(det.locator('.caf-tbd:not(.caf-tbd--mark)')).toHaveText(['확인 필요']);
  expect(await w(det.locator('.caf-mcell').first())).toBe(247);                  // (796 − 2 − 36 − 16) / 3
  expect(await h(det.locator('.caf-crit').first())).toBe(38);                    // min-height 36 + 선
  await page.mouse.move(10, 890);
  await shot(page, 'CA2_Info-new');
  // 확인 필요 풀기 → 다시 표시 · 기본 정보 고치기(규모 = 규모 · 매출)
  await det.getByRole('button', { name: '고객 접점 확인 필요 · 눌러서 확인 끝내기' }).click();
  await expect(det.locator('.caf-tbd:not(.caf-tbd--mark)')).toHaveCount(0);
  await det.locator('.caf-crit').last().hover();
  await det.getByRole('button', { name: '고객 접점 확인 필요로 표시' }).click();
  await expect(det.locator('.caf-tbd:not(.caf-tbd--mark)')).toHaveText(['확인 필요']);
  await det.getByRole('button', { name: '경쟁사 A 규모 고치기' }).click();
  await det.getByRole('textbox', { name: '경쟁사 A 규모' }).fill('대기업 · 매출 [위키 값]');
  await page.keyboard.press('Enter');
  await expect.poll(async () => {
    const a = comp(await getDoc(request, fid), '경쟁사 A');
    return [a.wiki.size, a.wiki.revenue, a.criteria.at(-1).status];
  }, { timeout: 10_000 }).toEqual(['대기업', '[위키 값]', 'check']);

  // CA2_Pc — 장단점 · 주장 포인트(줄 더하기 · 주장 축 고치기)
  await page.getByRole('tab', { name: '장단점 · 주장 포인트' }).click();
  await expect(page).toHaveURL(/\?tab=pc$/);
  await expect(det.locator('.caf-pcbox__h')).toHaveText(['경쟁사 장점 · 삼성 대비', '경쟁사 단점 · 삼성 대비']);
  await expect(det.locator('.caf-claims__h')).toHaveText('그래서 우리가 주장할 것');
  const addLine = async (btn: string, box: string, text: string) => {
    await det.getByRole('button', { name: btn }).click();
    await det.getByRole('textbox', { name: box }).fill(text);
    await page.keyboard.press('Enter');
    await expect(det.getByText(text, { exact: false }).first()).toBeVisible();
  };
  await addLine('+ 장점', '경쟁사 A 새 장점', '초기 도입가가 낮음 [견적 확인]');
  await addLine('+ 장점', '경쟁사 A 새 장점', '국내 유지보수 거점이 많음 [확인 필요]');
  await addLine('+ 단점', '경쟁사 A 새 단점', '사이니지 · IoT · 관제가 따로 놀아 공간 통합이 약함');
  await addLine('+ 단점', '경쟁사 A 새 단점', 'AI 오피스 레퍼런스가 적음');
  const claims: Array<[string, string]> = [
    ['통합', 'MagicINFO · SmartThings Pro · b.IoT 하나의 플랫폼으로 공간 7개를 묶음'],
    ['사례', '국내 AI 오피스 로비 도입사례로 RQ-01 ‘최초 AI Ready’ 뒷받침'],
    ['가격', '초기가는 높지만 원격 관리로 운영비 절감 — RQ-01'],
  ];
  for (const [i, [axis, text]] of claims.entries()) {
    await addLine('+ 주장', '새 주장', text);
    await det.getByRole('button', { name: `주장 ${i + 1} 축 고치기` }).click();
    await det.getByRole('textbox', { name: `주장 ${i + 1} 축` }).fill(axis);
    await page.keyboard.press('Enter');
    await expect(det.locator('.caf-claim .caf-axis').nth(i)).toHaveText(axis);
  }
  await expect(det.locator('.caf-pcbox--pro .caf-pcitem')).toHaveText(['· 초기 도입가가 낮음 [견적 확인]', '· 국내 유지보수 거점이 많음 [확인 필요]']);
  await expect.poll(async () => {
    const a = comp(await getDoc(request, fid), '경쟁사 A');
    return [a.pros.length, a.cons.length, a.claims.map((c: any) => [c.axis, c.supports])];
  }, { timeout: 10_000 }).toEqual([2, 2, [['통합', null], ['사례', null], ['가격', 'RQ-01']]]);
  expect(await w(det.locator('.caf-pcbox').first())).toBe(374);                  // (796 − 2 − 36 − 10) / 2
  await page.mouse.move(10, 890);
  await shot(page, 'CA2_Pc-new');

  // 저장 → CA_Done(보드 Done content=ca) · 허브 flow.json stages.ca
  await page.getByRole('tab', { name: '제안 기준 비교' }).click();
  await expect(page.locator('.wm-flow__summary')).toHaveText('경쟁사 3 · 비교 쌍 6');
  await page.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByRole('heading', { name: '경쟁사 분석을 저장했어요' })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText('경쟁사 3곳을 Storyboard에 담았어요')).toBeVisible();
  await expect(page.getByText(/"stages\.ca": \{/)).toBeVisible();
  await expect(page.locator('.wm-done__md pre')).toContainText('- 경쟁사 3 (직접 2 · AI 웹 탐색 1) · 비교 쌍 6');
  await expect(page.locator('.caf-nofollow')).toContainText('이 콘텐츠는 후속 작업이 없어요. Storyboard에서 다른 콘텐츠를 이어서 만들 수 있어요.');
  await expect(page.locator('.caf-nofollow').getByRole('link', { name: 'Storyboard로' })).toHaveAttribute('href', `/storyboard/flow/${sb.id}`);
  await expect(page.locator('.wm-done__stage--cur')).toContainText('경쟁사');
  doc = await getDoc(request, fid);
  expect(doc.status).toBe('done');
  expect(doc.ver).toBe(1);
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const sca = flow.stages.ca;
  expect(sca.ref).toBe(doc.code);
  expect(sca.ver).toBe(1);
  expect(sca.basis).toEqual({ from: dssRef, categories: ['사이니지', 'LED', '협업 디스플레이', '비디오월', 'IoT · 솔루션'] });
  expect(sca.dimensions).toEqual(['스펙', '가격', '유관 사례', 'ESG', '브랜드 평판']);
  expect(sca.competitors.map((c: any) => [c.id, c.name, c.by])).toEqual([['A', '경쟁사 A', 'manual'], ['B', '경쟁사 B', 'manual'], ['C', '경쟁사 C', 'ai-web']]);
  expect(sca.competitors[0].matches[0]).toEqual({ space: '로비 미디어월', ours: 'The Wall IAB 146"', theirs: '올인원 LED 월 · 동급 크기', dims: fill[0][3] });
  expect(sca.competitors[0].claims[2]).toEqual({ axis: '가격', text: '초기가는 높지만 원격 관리로 운영비 절감', supports: 'RQ-01' });
  expect(sca.competitors[0].criteria.at(-1)).toEqual({ k: '고객 접점', v: 'E 자산운용 거래 이력', status: 'check' });
  expect(sca.competitors[2].candidateEvidence).toMatchObject({ source: '업계 뉴스', date: '2026-08' });
  expect(sca.counts.competitors).toBe(3);
  expect(sca.counts.matches).toBe(6);
  expect(Object.values(sca.counts.verdicts).reduce((a: number, b) => a + (b as number), 0)).toBe(30);
  const cell = flow.cells.find((c: any) => c.key === 'ca');
  expect(cell).toMatchObject({ state: 'done', ref: doc.code, route: `/competitor/flow/${fid}` });
  expect(flow.cards.ca.facts[0]).toEqual(['경쟁사', '3']);
  // 보드 Done: 본문 좌우 80 → 카드 1020 · 요약 · JSON 상자 248 + 선
  expect(await w(page.locator('.wm-done__card'))).toBe(1020);
  expect(await h(page.locator('.wm-done__md'))).toBe(250);
  await page.mouse.move(10, 890);
  await shot(page, 'CA_Done-new');
  await page.getByRole('button', { name: '전체 JSON 보기' }).click();
  const dlg = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByText('"ca": {').first()).toBeVisible();
  await expect(dlg.locator('.wm-jsonline--add').first()).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'CA_DoneJson-new');
  await dlg.getByRole('button', { name: '닫기' }).last().click();

  // 다시 고치기 → 같은 문서(상단바 제목 = 코드) · 목록에 저장된 줄(코드 v1 · Storyboard 칩)
  await page.getByRole('button', { name: '다시 고치기' }).click();
  await expect(page.getByRole('heading', { name: '경쟁사를 리스트업하고 우리 제안과 비교해요' })).toBeVisible();
  await expect(page.locator('.caf-row')).toHaveCount(4);
  await page.goto('/competitor');
  const row = page.getByRole('row').filter({ hasText: `${doc.code} v1` });
  await expect(row).toBeVisible();
  await expect(row.getByRole('button', { name: sb.name })).toBeVisible();
  await expect(row.getByRole('link', { name: '열기' })).toHaveAttribute('href', `/competitor/flow/${fid}`);
});

test('CA 새 흐름 — Storyboard 「만들기」(?sb=&auto=1) · 1920 폭 · AI 후보 없음 · 이전 흐름 경로', async ({ page, request }) => {
  budget(120_000);
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await makeStoryboard(request, { dss: true, name: `판교 스타트업 단지 ${tag()}` });

  // Storyboard 화면의 「만들기」 → Gate 를 건너뛰고 바로 만든다(CF-07)
  await page.goto(`/competitor/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/competitor\/flow\/cflow_[0-9A-Za-z]+$/, { timeout: 20_000 });
  await expect(page.locator('.caf-cat')).toHaveText(['사이니지 3', 'LED 1', '협업 디스플레이 1', '키오스크 1', 'IoT · 솔루션 2']);
  await expect(page.getByText('경쟁사를 고르거나 추가해요')).toBeVisible();

  // 1920 폭에서도 본문 열은 1180 · 고정 칸 290 (UI-W-01 · UI-W-04)
  await page.setViewportSize({ width: 1920, height: 1080 });
  expect(await widths(page)).toEqual({ flow: 1180, left: 290, detail: 796 });
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

  // 위키에 없는 회사 → 기본 정보는 모두 자리표시 · 비교 쌍 없음 → 「+ 비교 쌍」 · 빼기는 묻는다
  await page.getByLabel('경쟁사 추가').fill('모르는 회사');
  await page.getByLabel('경쟁사 추가').press('Enter');
  const det = page.locator('.caf-detail');
  await expect(det.locator('.caf-dname')).toContainText('모르는 회사', { timeout: 20_000 });
  await expect(det.getByText('비교 쌍이 없어요', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: '+ 비교 쌍' }).click();
  await page.getByRole('group', { name: '비교 쌍 추가' }).getByLabel('우리 제품 · 솔루션(DSS)').selectOption('삼성 키오스크');
  await page.getByRole('group', { name: '비교 쌍 추가' }).getByRole('button', { name: '추가' }).click();
  await expect(det.locator('.caf-ours')).toHaveText(['삼성 키오스크']);
  await expect(det.locator('.caf-theirs')).toHaveText(['↔ [확인 필요]']);
  await expect(det.locator('.caf-where')).toHaveText(['로비']);
  await page.getByRole('tab', { name: '개요 · 선별 기준' }).click();
  await expect(det.locator('.caf-mcell__v')).toHaveText(['[확인 필요]', '[확인 필요] · 매출 [위키 값]', '[위키 값]', '[확인 필요]', '[확인 필요]', '[확인 필요]']);
  await page.locator('.caf-row').first().hover();
  await page.getByRole('button', { name: '모르는 회사 빼기' }).click();
  const confirmDlg = page.getByRole('dialog', { name: /모르는 회사를 목록에서 뺄까요/ });
  await expect(confirmDlg).toBeVisible();
  await confirmDlg.getByRole('button', { name: '빼기' }).click();
  await expect(page.locator('.caf-row')).toHaveCount(0);

  // 이전 흐름: 정의서 진입(?input=requirements)은 이전 넣기 화면으로 · 이전 목록은 /competitor/legacy
  await page.goto('/competitor/new?input=requirements');
  await expect(page).toHaveURL(/\/competitor\/legacy\/new\?input=requirements$/);
  await page.goto('/competitor/legacy');
  await expect(page.getByRole('heading', { name: '경쟁사 분석 작업' })).toBeVisible();
  await expect(page.getByRole('link', { name: '새 분석' })).toHaveAttribute('href', '/competitor/legacy/new');
});
