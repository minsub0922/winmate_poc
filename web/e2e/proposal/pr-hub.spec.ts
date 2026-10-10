/**
 * 허브 Storyboard(SB-nn, 새 콘텐츠 흐름)에서 제안서 시작(2026-10-10) — 실제 백엔드(게이트웨이) · mock 모델.
 * Storyboard(rq → dss → Key message → mi · ca · vp · sp · sc, API) → `/proposal/new?sb=` → PR1L(Storyboard 줄 + 연결된 콘텐츠 · 넣을 곳 ·
 * 연결하면 채워지는 것) → 연결 · 다음 → PR2 표준 → PR3 시트 구성 → 섹션(MI · Value Props · 공간별 제품 · Why Samsung · 제품 스펙)이 stage 값으로 채워짐
 * → 허브 「PPT 제작 · B2B 제안서」 칸(stages.ppt). 값 모양은 docs/scenarios/11-content-flow.md §6.
 * 실행: cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=proposal WM_E2E_DEV=1 WM_E2E_PORT=5210 npx playwright test e2e/proposal/pr-hub.spec.ts --workers=1
 */
import { expect as baseExpect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { internalHeaders, makeStoryboard, tag } from '../shell/flowkit';
import { PR_ID, api, backendDown, isolateBrokenFeatures, removeProposal, shot } from './helpers';

const expect = baseExpect.configure({ timeout: 20_000 });
test.describe.configure({ mode: 'serial', timeout: 240_000 });
test.use({ actionTimeout: 30_000, navigationTimeout: 60_000 });
test.beforeEach(async ({ page }) => { await isolateBrokenFeatures(page); });

const T = tag();
const REF = { mi: `MI-${T}`, ca: `CA-${T}`, vp: `VP-${T}`, sp: `SP-${T}`, sc: `SC-${T}` };
const KM = 'AI Ready 오피스의 새로운 모델';
const PILLARS = [{ text: '사람을 알아보는 공간', evidence: ['RQ-01 대표이사 1'] }, { text: '에너지 20% 절감을 숫자로', evidence: ['RQ-01 대표이사 3'] }];
const dims = (...v: Array<[string, string]>) => Object.fromEntries(['spec', 'price', 'cases', 'esg', 'brand'].map((k, i) => [k, { verdict: v[i][0], note: v[i][1] }]));

const STAGES: Record<keyof typeof REF, { value: Record<string, unknown>; title: string; line: string }> = {
  mi: {
    title: '용산 오피스 시장 분석', line: '담은 정보 3 · 수치 확인 1',
    value: {
      prevVer: null, queries: { market: ['프라임 오피스 스마트 빌딩'], customer: ['E 자산운용 ESG'], user: ['하이브리드 근무 회의실'] },
      filters: { period: '최근 1년', sourceTypes: ['리포트', '공시 · IR', '뉴스'] }, counts: { found: 4, kept: 3, numberCheck: 1 },
      items: [
        { id: 'mi-1', group: '시장', summary: '프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석', source: { type: '리포트', name: '부동산 리서치', date: '2026-08', url: 'https://example.com/report' }, kept: true, addedIn: 'v1', numberCheck: null },
        { id: 'mi-2', group: '고객', summary: 'E 자산운용은 운용 자산의 에너지 사용량을 30% 줄이겠다고 밝힘', source: { type: '공시 · IR', name: 'E 자산운용 ESG 보고서', date: '2026-05', url: 'https://example.com/esg' }, kept: true, addedIn: 'v1', numberCheck: '수치 확인' },
        { id: 'mi-3', group: '사용자', summary: '하이브리드 근무로 회의실 예약이 오후에 몰림', source: { type: '뉴스', name: '오피스 뉴스', date: '2026-07', url: 'https://example.com/news' }, kept: true, addedIn: 'v1', numberCheck: null },
        { id: 'mi-4', group: '시장', summary: '빼 둔 정보 — 제안서에 들어가면 안 됨', source: { type: '뉴스', name: '다른 뉴스', date: '2026-01', url: 'https://example.com/x' }, kept: false, addedIn: 'v1', numberCheck: null },
      ],
    },
  },
  ca: {
    title: '용산 오피스 경쟁사', line: '경쟁사 2 · 비교 쌍 3',
    value: {
      basis: { from: 'DSS', categories: ['사이니지', 'LED'] }, dimensions: ['스펙', '가격', '유관 사례', 'ESG', '브랜드 평판'],
      competitors: [
        { id: 'A', name: '경쟁사 A', by: 'manual', wiki: { hq: '국내', size: '대기업', industry: '전자 · 디스플레이', mainBusiness: '상업용 디스플레이 · LED 월', source: { type: 'Wikipedia', url: 'https://ko.wikipedia.org/' } },
          criteria: [{ k: '제품군', v: '사이니지 · LED 월', status: 'ok' }],
          matches: [
            { space: '로비 미디어월', ours: 'The Wall IAB 146"', theirs: '올인원 LED 월', dims: dims(['similar', '해상도 동급'], ['ours-worse', '초기가 높음'], ['ours-better', '국내 AI 오피스 로비 사례'], ['ours-better', '저전력'], ['similar', '비슷']) },
            { space: '콘텐츠 관리', ours: 'MagicINFO', theirs: '자사 CMS', dims: dims(['ours-better', '원격 일괄 배포'], ['similar', '비슷'], ['ours-better', '대형 오피스 사례'], ['no-data', '자료 없음'], ['similar', '비슷']) },
          ],
          pros: ['초기 도입가가 낮음'], cons: ['사이니지 · IoT 가 따로 놀아 공간 통합이 약함'],
          claims: [{ axis: '통합', text: 'MagicINFO · SmartThings Pro 하나의 플랫폼으로 공간을 묶음', supports: ['RQ-01'] }] },
        { id: 'B', name: '경쟁사 B', by: 'ai-web', wiki: { hq: '해외', size: '[위키 값]' },
          matches: [{ space: '회의실', ours: 'Flip Pro WA75D', theirs: '전자칠판', dims: dims(['similar', '판서 동급'], ['similar', '가격 비슷'], ['ours-worse', '회의실 단독 사례가 더 많음'], ['similar', '비슷'], ['similar', '비슷']) }],
          pros: [], cons: [], claims: [] },
      ],
      counts: { competitors: 2, matches: 3, verdicts: { oursBetter: 4, similar: 9, oursWorse: 2, noData: 1 } },
    },
  },
  vp: {
    title: '용산 오피스 가치 맵', line: '항목 2 · 가치 2 · 니즈 1',
    value: {
      from: 'DSS', selection: { fromDss: 3, excluded: [], addedOutsideDss: [] },
      items: [
        { name: 'The Wall IAB 146"', kind: 'product', ref: null, spaces: ['로비'], values: [
          { id: 'vp-1', space: '로비', message: '들어서는 순간 회사의 AI 비전을 보여 줌', need: { text: '방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요', by: 'manual' }, req: 'RQ-01 최초 AI Ready', by: 'manual' }] },
        { name: 'MagicINFO', kind: 'solution', ref: 'kb:solution:sol_magicinfo', spaces: ['회의실'], values: [
          { id: 'vp-2', space: '회의실', message: '회의실 화면을 본사에서 한 번에 관리', need: null, req: '', by: 'ai-accepted' }] },
      ],
      importedFrom: [], counts: { items: 2, values: 2, needs: 1, needsMissing: 1 },
    },
  },
  sp: {
    title: '용산 오피스 스펙 비교', line: '제품 2 · 항목 2 · 경고 1',
    value: {
      from: 'DSS', format: '비교표', lang: 'ko', unit: 'mm',
      columns: [{ key: 'size_resolution', label: '화면 크기 · 해상도' }, { key: 'brightness_contrast', label: '밝기 · 명암비' }],
      models: [
        { space: '로비', name: 'Smart Signage QM55C', model_code: 'LH55QMCEBGCXKR', ref: 'kb:model:LH55QMCEBGCXKR', qty: 2, specs: { size_resolution: '55" · 3840×2160', brightness_contrast: '500nit · 4000:1' }, by: 'manual' },
        { space: '회의실', name: 'Flip Pro WA75D', model_code: null, ref: null, qty: null, specs: { size_resolution: '[확인 필요]', brightness_contrast: '[확인 필요]' }, by: 'manual' },
      ],
      warnings: [{ model: 'Flip Pro WA75D', kind: 'not_in_catalog', text: '카탈로그에 없는 모델' }],
      counts: { models: 2, columns: 2, warnings: 1 },
    },
  },
  sc: {
    title: '용산 오피스 공간 시나리오', line: '공간 2 · 시나리오 2',
    value: {
      from: 'DSS',
      spaces: [
        { name: '로비', products: ['The Wall IAB 146"', 'Smart Signage QM55C', 'MagicINFO'], scenarios: [
          { id: 'sc-1', title: '방문객 첫 안내', user: '방문객', products: ['The Wall IAB 146"', 'MagicINFO'],
            steps: [{ text: '로비에 들어서면 미디어월이 환영 영상을 보여 줌', product: 'The Wall IAB 146"' }, { text: '안내 사이니지가 회의실 위치를 알려 줌', product: 'Smart Signage QM55C' }], fields: [], by: 'manual' }] },
        { name: '회의실', products: ['Flip Pro WA75D'], scenarios: [
          { id: 'sc-2', title: '하이브리드 회의', user: '직원', products: ['Flip Pro WA75D'], steps: [{ text: '회의 시작 전 자료를 화면에 띄움', product: 'Flip Pro WA75D' }], fields: [], by: 'manual' }] },
      ],
      rules: { minProductsPerSpace: 1, minProductsPerScenario: 1 }, counts: { spaces: 2, scenarios: 2 },
    },
  },
};

/** 허브 Storyboard — rq · dss(flowkit) + Key message + mi · ca · vp · sp · sc stage(서비스 전용 PUT, 내부 토큰) */
async function hubStoryboard(request: APIRequestContext) {
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${T}` });
  const r = await request.patch(`/api/storyboard/v1/flows/${sb.id}`, { data: { key_message: KM, key_pillars: PILLARS } });
  expect(r.ok(), await r.text()).toBe(true);
  for (const key of Object.keys(REF) as Array<keyof typeof REF>) {
    const st = STAGES[key];
    const s = await request.put(`/api/storyboard/v1/flows/${sb.id}/stages/${key}`, {
      headers: internalHeaders('mi'),
      data: { ref: REF[key], ver: 1, value: st.value, md: `- ${st.line}`, title: st.title, card: { title: st.title, facts: [], groups: [], line: st.line } },
    });
    expect(s.ok(), `${key} ${s.status()} ${await s.text()}`).toBe(true);
  }
  return sb;
}

const w = async (l: Locator) => Math.round((await l.boundingBox())!.width);
const h = async (l: Locator) => Math.round((await l.boundingBox())!.height);

async function displayOf(request: APIRequestContext, id: string, sheetId: string) {
  const sh = await api(request, 'GET', `/proposals/${id}/sheets/${sheetId}`);
  return JSON.stringify(sh.display);
}

/** 섹션 화면 — 들어가면 연결 자료(허브)로 초안을 쓴다(section_fill 잡) → 카드가 다 쓰일 때까지 */
async function openSection(page: Page, request: APIRequestContext, id: string, key: string) {
  await page.goto(`/proposal/${id}/sections/${key}`);
  await expect(page.getByTestId('pr-section')).toBeVisible({ timeout: 60_000 });
  await expect.poll(async () => (await api(request, 'GET', `/proposals/${id}/sections/${key}`)).status, { timeout: 90_000 }).toBe('ready');
  await page.reload();
  await expect(page.getByTestId('pr-sheet-card').first()).toBeVisible();
  return api(request, 'GET', `/proposals/${id}/sections/${key}`);
}

let id: string | null = null;
let sbId: string | null = null;
test.afterAll(async ({ request }) => { await removeProposal(request, id); });

test('허브 Storyboard → /proposal/new?sb= → PR1L(연결된 콘텐츠 · 넣을 곳 · 연결하면 채워지는 것) → PR2 → PR3', async ({ page, request }) => {
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
  const sb = await hubStoryboard(request);
  sbId = sb.id;
  const dssRef = (await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.dss.ref as string;

  await page.goto(`/proposal/new?sb=${encodeURIComponent(sb.id)}`);
  await expect(page).toHaveURL(new RegExp(`/proposal/${PR_ID.source}/works$`), { timeout: 30_000 });
  id = page.url().match(PR_ID)![0];
  await expect(page.getByTestId('pr1l')).toBeVisible();
  // 고객 정보는 stages.rq 에서 미리 채움
  const p0 = await api(request, 'GET', `/proposals/${id}`);
  expect(p0.customer.name).toBe('E 자산운용');
  expect(p0.title).toBe('용산 업무시설 재개발 AI Ready 오피스');
  expect(p0.customer.decision_makers).toBe('대표이사, 공간컨텐츠실장, 개발사업팀장');
  expect(p0.start_mode).toBe('works');

  // Storyboard 줄(켜짐) + 연결된 콘텐츠 8줄(요구사항 · DSS · Key message · MI · 경쟁사 · VP · Spec · 시나리오)
  const row = page.locator(`[data-testid="pr1l-hub"][data-ref="${sb.id}"]`);
  await expect(row).toBeVisible();
  await expect(row.getByRole('checkbox', { name: sb.name })).toBeChecked();
  await expect(row.getByTestId('pr1l-work')).toContainText(`Storyboard · ${sb.id} · DSS + 콘텐츠 5/5`);
  await expect(row.getByTestId('pr1l-work')).toContainText('고객 정보 · 섹션 6');
  const items = row.getByTestId('pr1l-hub-content');
  await expect(items).toHaveCount(8);
  expect(await items.evaluateAll((els) => els.map((e) => e.getAttribute('data-key')))).toEqual(['rq', 'dss', 'km', 'mi', 'ca', 'vp', 'sp', 'sc']);
  const to = async (k: string) => (await row.locator(`[data-key="${k}"] .pr-tochip`).textContent())?.trim();
  expect(await to('rq')).toBe('고객 정보');
  expect(await to('dss')).toBe('공간별 제품 · 솔루션 제안');
  expect(await to('km')).toBe('Value Props');
  expect(await to('mi')).toBe('MI');
  expect(await to('ca')).toBe('Why Samsung');
  expect(await to('sp')).toBe('제품 스펙');
  expect(await to('sc')).toBe('솔루션 제안');
  await expect(row.locator('[data-key="mi"]')).toContainText(`Market Intelligence · ${REF.mi} v1 · 담은 정보 3 · 수치 확인 1`);
  await expect(row.locator('[data-key="mi"] .pr-workrow__title')).toHaveText('용산 오피스 시장 분석');
  await expect(row.locator('[data-key="km"] .pr-workrow__title')).toHaveText(KM);
  // 연결하면 채워지는 것 — 고객 출처 · 섹션별 채움(stage 코드)
  const pv = page.getByTestId('pr1l-preview');
  await expect(page.getByTestId('pr1l-cust-from')).toHaveText('고객 · 프로젝트 · Storyboard에서');
  await expect(pv).toContainText('E 자산운용 · 오피스');
  await expect(pv).toContainText('요구사항 3건');
  const fill = await pv.locator('.pr-fillrow').evaluateAll((els) => els.map((e) => [e.getAttribute('data-state'), e.textContent]));
  const st = Object.fromEntries(fill.map(([s, t]) => [t, s]));
  const standard = fill.length === 8;
  if (standard) {
    expect(st[`Market Intelligence${REF.mi}`]).toBe('full');
    expect(st[`Value Props${REF.vp}`]).toBe('full');
    expect(st['조감도새로 작성']).toBe('new');
    expect(st[`공간별 제품${dssRef}`]).toBe('full');
    expect(st[`솔루션 제안${dssRef}`]).toBe('partial');
    expect(st['유관 사례새로 찾기']).toBe('new');
    expect(st[`Why Samsung${REF.ca}`]).toBe('full');
    expect(st[`제품 스펙${REF.sp}`]).toBe('full');
  }
  // 보드 PR1L px: 목록 1fr + 채워지는 것 248 · 머리 42 · 작업 줄 54 · 아이콘 32 · 넣을 곳 140 · 채움 줄 27
  expect(await w(pv)).toBe(248);
  expect(await h(page.locator('.pr-workbox__head'))).toBe(42);
  expect(await h(row.getByTestId('pr1l-work'))).toBe(54);
  expect(await h(items.first())).toBe(54);
  expect(await w(items.first().locator('.pr-workrow__icon'))).toBe(32);
  expect(await w(items.first().locator('.pr-workrow__to'))).toBe(140);
  expect(await h(pv.locator('.pr-fillrow').first())).toBe(27);
  expect(await w(page.getByTestId('pr1l-dock'))).toBe(800);
  await shot(page, 'PR1L-hub-new');

  // 연결 · 다음 → PR2(표준) → PR3
  await page.getByTestId('pr1l-next').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/type$`), { timeout: 60_000 });
  await expect(page.getByTestId('pr2')).toBeVisible();
  await expect(page.getByTestId('pr2-summary')).toContainText('E 자산운용');
  await shot(page, 'PR2-hub-new');
  await page.getByTestId('pr2-type-standard').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/compose`));
  await expect(page.getByTestId('pr3-list')).toBeVisible();
  for (const k of ['mi', 'vp', 'birdseye', 'spaceProducts', 'solution', 'cases', 'why', 'spec']) await expect(page.getByTestId(`pr3-sec-${k}`)).toBeVisible();
  await shot(page, 'PR3-hub-new');
  // 허브 「PPT 제작 · B2B 제안서」 칸에 이 제안서
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  expect(flow.stages.ppt.proposal_id).toBe(id);
  expect(flow.cells.find((c: { key: string }) => c.key === 'ppt')).toMatchObject({ state: 'done', route: `/proposal/${id}` });

  await page.getByTestId('pr3-start').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/(industry|sections/mi)`), { timeout: 30_000 });
  if (page.url().includes('/industry')) await page.getByTestId('pr3i-apply').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${id}/sections/mi`), { timeout: 30_000 });
});

test('섹션이 허브 stage 값으로 채워진다 — MI · Value Props · 공간별 제품 · Why Samsung · 제품 스펙', async ({ page, request }) => {
  test.skip(!id || !sbId, '앞 테스트가 제안서를 만들지 못했어요');
  const pid = id!;
  // MI — 담은 정보만 · 출처 · 수치 확인은 확정 필요
  let sv = await openSection(page, request, pid, 'mi');
  await expect(page.getByTestId('pr-source')).toHaveCount(1);
  await expect(page.getByTestId('pr-source')).toContainText(`Storyboard · ${REF.mi}`);
  const ms = sv.sheets.find((s: { role: string }) => s.role === 'MS');
  const msd = await displayOf(request, pid, ms.id);
  expect(msd).toContain('프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석');
  expect(msd).toContain('부동산 리서치');
  expect(msd).not.toContain('빼 둔 정보');
  const cb = await api(request, 'GET', `/proposals/${pid}/sheets/${sv.sheets.find((s: { role: string }) => s.role === 'CB').id}`);
  expect(JSON.stringify(cb.display)).toContain('30%');
  expect(cb.confirm_items.length).toBeGreaterThan(0);
  await shot(page, 'PRS1-hub-new');

  // Value Props — Key message + 받쳐 줄 메시지 · 고객 니즈
  sv = await openSection(page, request, pid, 'vp');
  await expect(page.getByTestId('pr-source')).toHaveCount(1);
  await expect(page.getByTestId('pr-source')).toContainText(`Storyboard · Key message · ${REF.vp}`);
  const vpd = await displayOf(request, pid, sv.sheets.find((s: { role: string }) => s.role === 'VP').id);
  for (const t of [KM, '사람을 알아보는 공간', '에너지 20% 절감을 숫자로']) expect(vpd).toContain(t);
  const chd = await displayOf(request, pid, sv.sheets.find((s: { role: string }) => s.role === 'CH').id);
  expect(chd).toContain('방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요');
  await shot(page, 'PRS2-hub-new');

  // 공간별 제품 — DSS 공간 · 제품 · 수량 문자열(모르는 수량은 [확인 필요])
  sv = await openSection(page, request, pid, 'spaceProducts');
  await expect(page.getByTestId('pr-source').first()).toContainText('Storyboard · DSS-');
  expect(sv.sheets.filter((s: { role: string }) => s.role === 'PI').map((s: { title: string }) => s.title)).toEqual(['로비', '회의실', '주차장']);
  const smd = await displayOf(request, pid, sv.sheets.find((s: { role: string }) => s.role === 'SM').id);
  for (const t of ['The Wall IAB 146', '1식', 'Smart Signage QM55C 2대', '삼성 키오스크']) expect(smd).toContain(t);
  expect(smd).not.toContain('LH55QMCEBGCXKR');                              // 공간 맵은 제품 이름(모델 코드는 스펙에서)
  const meet = await displayOf(request, pid, sv.sheets.find((s: { title: string }) => s.title === '회의실').id);
  expect(meet).toContain('Flip Pro WA75D');
  expect(meet).toContain('[확인 필요]');
  await shot(page, 'PRS4-hub-new');

  // Why Samsung — 판정 · 강점 · 익명
  sv = await openSection(page, request, pid, 'why');
  await expect(page.getByTestId('pr-source')).toHaveCount(1);
  await expect(page.getByTestId('pr-source')).toContainText(`Storyboard · ${REF.ca}`);
  const cmd = await displayOf(request, pid, sv.sheets.find((s: { role: string }) => s.role === 'CM').id);
  for (const t of ['경쟁사 A', '경쟁사 B', '유관 사례', '삼성 우위']) expect(cmd).toContain(t);
  const std = await displayOf(request, pid, sv.sheets.find((s: { role: string }) => s.role === 'ST').id);
  expect(std).toContain('하나의 플랫폼으로 공간을 묶음');
  await shot(page, 'PRS7-hub-new');

  // 제품 스펙 — 모델 × 항목 · 경고
  sv = await openSection(page, request, pid, 'spec');
  await expect(page.getByTestId('pr-source')).toHaveCount(1);
  await expect(page.getByTestId('pr-source')).toContainText(`Storyboard · ${REF.sp}`);
  const scd = await displayOf(request, pid, sv.sheets.find((s: { role: string }) => s.role === 'SC').id);
  for (const t of ['Smart Signage QM55C', 'Flip Pro WA75D', '화면 크기 · 해상도', '3840×2160', '카탈로그에 없는 모델']) expect(scd).toContain(t);
  await shot(page, 'PRS8-hub-new');

  // 미리보기(PR7P) — 시트에 들어간 허브 값이 그려진다(Value Props · 경쟁 비교 · 스펙 비교)
  const scSheet = await api(request, 'GET', `/proposals/${pid}/sheets/${sv.sheets.find((s: { role: string }) => s.role === 'SC').id}`);
  for (const [role, sec, name] of [['VP', 'vp', 'PR7P-hub-vp-new'], ['CM', 'why', 'PR7P-hub-cm-new'], ['SC', 'spec', 'PR7P-hub-sc-new']] as const) {
    const s2 = (await api(request, 'GET', `/proposals/${pid}/sections/${sec}`)).sheets.find((x: { role: string }) => x.role === role);
    await page.goto(`/proposal/${pid}/preview/${s2.sheet_no}`);
    await expect(page.getByTestId('pr7p-preview')).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId('pr7p-preview')).toContainText(role === 'VP' ? '사람을 알아보는 공간' : role === 'CM' ? '경쟁사 A' : '3840×2160', { timeout: 20_000 });
    await shot(page, name);
  }
  expect(scSheet.section_key).toBe('spec');

  // 허브에 없는 조감도 섹션은 연결 자료 없음(새로 작성)
  await page.goto(`/proposal/${pid}/sections/birdseye`);
  await expect(page.getByTestId('pr-no-sources')).toBeVisible({ timeout: 30_000 });
});

test('홈 「B2B 제안서 만들기」(/proposal/new) → PR1 최근 Storyboard 카드 「채우기」 → PR1L 에 그 허브 Storyboard 가 켜진 채', async ({ page, request }) => {
  test.skip(!sbId, '앞 테스트가 허브 Storyboard 를 만들지 못했어요');
  let blank: string | null = null;
  try {
    await page.goto('/proposal/new');
    await expect(page).toHaveURL(new RegExp(`/proposal/${PR_ID.source}/customer$`), { timeout: 30_000 });
    blank = page.url().match(PR_ID)![0];
    await page.getByLabel('고객사').fill('E 자산운용');
    // 카드가 고르는 Storyboard = workspace 색인 SB 중 최근 30일 · 고객사 일치(제목 · meta.customer · 요약) 첫 항목(허브는 요약에 고객사)
    const items = (await (await request.get('/api/workspace/v1/items?feature=SB&limit=20')).json()).items as Array<{ item_id: string; title: string; summary?: string; meta?: { customer?: string } }>;
    const pick = items.find((it) => it.title.includes('E 자산운용') || String(it.meta?.customer ?? '').includes('E 자산운용') || String(it.summary ?? '').includes('E 자산운용'));
    test.skip(!pick, '고객사가 맞는 최근 Storyboard 가 없어요');
    const card = page.getByTestId('pr1-sb');
    await expect(card).toBeVisible();
    await expect(card).toContainText(pick!.title);
    await card.getByRole('button', { name: '채우기' }).click();
    await expect(page).toHaveURL(new RegExp(`/proposal/${blank}/works`), { timeout: 20_000 });
    if (/^SB-\d+$/.test(pick!.item_id)) {
      const row = page.locator(`[data-testid="pr1l-hub"][data-ref="${pick!.item_id}"]`);
      await expect(row.getByRole('checkbox').first()).toBeChecked();
      await expect(row.getByTestId('pr1l-hub-content').first()).toBeVisible();
      await expect.poll(async () => (await api(request, 'GET', `/proposals/${blank}/links`)).links.map((l: { ref_id: string }) => l.ref_id), { timeout: 15_000 }).toContain(pick!.item_id);
    }
  } finally {
    await removeProposal(request, blank);
  }
});
