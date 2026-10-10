/**
 * Storyboard 새 흐름(2026-10-08 보드 webapp1 SB0 · SB1 · SB1_Json · SB1_View · SB1_Strat · SB1_StratAI) — 실제 허브(storyboard `/v1/flows*`, mock 모델).
 * 사전 작업은 API 로 넣는다(내부 전용 경로 · 콘텐츠 서비스 이름으로): 요구사항 → DSS → MI(보드 SB-01 문장) · MI 에서 분기(SB-02 · MI-02 리테일 테넌트 관점).
 * SB0 목록 → SB1(진행 8칸 · 연결된 콘텐츠 · 요약본 md) → 보기 팝업(페이지 이동 없음) → json 탭 → 전략 수립 → AI 후보 3안 → 이 안 쓰기 → 저장 →
 * 요약본 수정(✎ 유지) → 만들기 링크(`/<base>/new?sb=&auto=1`) → 분기 n · 분기 Storyboard.
 * 보드 고정 칸(SB0 300 · 120 · 110 / SB1 오른쪽 470 · 칸 56 · 줄 50 · 이름 120 · 팝업 1100×700 · 후보 360)을 숫자로 재고 __screens__/<보드>-new.png 로 남긴다.
 * 실행: cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=storyboard WM_E2E_DEV=1 WM_E2E_PORT=5202 npx playwright test e2e/storyboard/sb-flow.spec.ts --workers=1
 */
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { internalHeaders, tag } from '../shell/flowkit';
import { shot } from './fixtures';

test.describe.configure({ timeout: 120_000 });

const w = async (l: Locator) => Math.round((await l.boundingBox())!.width);
const h = async (l: Locator) => Math.round((await l.boundingBox())!.height);
const x = async (l: Locator) => Math.round((await l.boundingBox())!.x);
/** 「SB-02와 공유」 · 「SB-61과 공유」 — 끝 숫자 받침(0 1 3 6 7 8)에 따라 */
const wa = (id: string) => `${id}${/[013678]$/.test(id) ? '과' : '와'}`;

/** 보드 ContentPopup · SB1 문장(용산 AI Ready 오피스) */
const RQ_CARD = {
  title: '용산 업무시설 재개발 AI Ready 오피스',
  facts: [['고객사', 'E 자산운용'], ['최종 제안대상', '대표이사'], ['요구', '12 · 확인 필요 4']],
  groups: [
    { h: '대표이사', sub: '50%', lines: [{ t: '사용자를 인식하고 반응하는 AI Ready 오피스' }, { t: '최초 AI Ready 공간으로 알리기' }, { t: '에너지 사용량 20% 절감 · 실측 증빙' }] },
    { h: '공간컨텐츠실장', sub: '30%', lines: [{ t: '오피스를 업무환경 플랫폼으로', note: '확인 필요' }, { t: '예측 · 반응형 공간' }, { t: '건물 가치 · 임대 선호도 제고' }] },
    { h: '개발사업팀장', sub: '20%', lines: [{ t: 'AI 인프라를 설계 단계에 반영' }, { t: '시공 · 운영 유지보수 부담 최소화' }] },
  ],
  foot: '제작자 의견은 고객 문서에서 빠져요',
  line: '키맨 3 · 요구 12 · 확인 필요 4',
};
const DSS_CARD = {
  title: '용산 오피스 공간별 제품',
  facts: [['업종', '오피스 · 업무시설'], ['공간 · 제품', '7 · 12'], ['솔루션', 'MagicINFO · SmartThings Pro · b.IoT']],
  groups: [
    { h: '로비', sub: '제품 3', lines: [{ t: 'The Wall IAB 146" · 1식' }, { t: 'Smart Signage QM55C · 2대' }, { t: '삼성 키오스크 · 1대' }] },
    { h: '회의실 · 사무실', sub: '제품 4', lines: [{ t: 'Flip Pro WA75D · 실 수', note: '확인 필요' }, { t: 'Smart Signage QB55C · 실당 1대' }, { t: '스마트 모니터 · 좌석 수', note: '확인 필요' }] },
    { h: '그 밖의 공간', sub: '제품 5', lines: [{ t: '라운지 QM55C · 중앙관제실 비디오월 VM55B' }, { t: '공용공간 SmartThings 센서 · QB43C' }, { t: '주차장 옥외형 사이니지 OHC55', note: '확장' }] },
  ],
  foot: '수량 [확인 필요] 3곳 · 확장 공간 1',
  line: '오피스 · 공간 7 · 제품 12 · 솔루션 3',
};
const MI_CARD = {
  title: '용산 오피스 시장 분석',
  facts: [['담은 정보', '11'], ['출처', '11 · 링크 포함'], ['수치 원문 확인', '2']],
  groups: [
    { h: '시장', sub: '4', lines: [{ t: '프라임 오피스 스마트 빌딩 도입 증가', note: '리포트' }, { t: 'AI 도입 기업의 회의 · 협업 공간 확대', note: '리포트' }, { t: '오피스 로비의 브랜드 공간화', note: '뉴스' }] },
  ],
  foot: '문장은 원문을 줄여 쓴 것 · 수치는 원문 확인',
  line: '담은 정보 11 · 출처 11',
};
const RQ_VAL = {
  customer: 'E 자산운용', title: RQ_CARD.title, target: '대표이사',
  keymen: [
    { role: '대표이사', weight: 50, needs: ['사용자를 인식하고 반응하는 AI Ready 오피스', '최초 AI Ready 공간으로 알리기'] },
    { role: '공간컨텐츠실장', weight: 30, needs: ['오피스를 업무환경 플랫폼으로'] },
    { role: '개발사업팀장', weight: 20, needs: ['AI 인프라를 설계 단계에 반영'] },
  ],
  goals: ['AI Ready 오피스의 새로운 모델'],
  requirements: [{ id: 'R1', text: '사용자를 인식하고 반응하는 AI Ready 오피스', status: 'ok', by: 'manual' }],
  counts: { keymen: 3, reqs: 12, check: 4 },
};
const DSS_VAL = {
  industry: { value: '오피스 · 업무시설', by: 'manual', basis: null },
  spaces: [{ name: '로비', by: 'manual', products: [{ name: 'The Wall IAB 146"', kind: 'product', ref: null, qty: '1식', by: 'manual' }] }],
  solutions: [{ name: 'MagicINFO', ref: null, by: 'manual', links: [], why: null }],
  counts: { spaces: 7, products: 12, solutions: 3 },
};
const RQ_MD = '- 대표이사(50%): 사용자를 인식하고 반응하는 오피스 · 최초 AI Ready로 알리기\n- 공간컨텐츠실장(30%): 업무환경 플랫폼 [확인 필요]\n- 개발사업팀장(20%): 설계 단계 AI 인프라 · 유지보수 최소화';
const DSS_MD = '- 업종: 오피스 · 업무시설 / 공간 7\n- 로비: The Wall IAB 146" · QM55C ×2 · 키오스크\n- 솔루션: MagicINFO · SmartThings Pro · b.IoT';
const MI_MD = '## Market Intelligence · MI\n- 담은 정보 11 (시장 4 · 고객사 4 · 사용자 3)';
const KM = 'AI Ready 오피스의 새로운 모델';
const NAME = '용산 AI Ready 오피스';

async function ok(r: Awaited<ReturnType<APIRequestContext['get']>>, what: string) {
  if (!r.ok()) throw new Error(`${what} → ${r.status()} ${await r.text()}`);
  return r.json();
}

/** 보드 SB-01 모양의 Storyboard(요구사항 · DSS · MI + Key message)와 MI 에서 분기한 SB-02(MI-02) */
async function seed(request: APIRequestContext) {
  const t = tag().toUpperCase();
  const refs = { rq: `RQ-${t}`, dss: `DSS-${t}`, mi: `MI-${t}`, mi2: `MI-${t}B` };
  const main = await ok(await request.post('/api/storyboard/v1/flows', {
    headers: internalHeaders('requirements'),
    data: { name: NAME, customer: 'E 자산운용', target: '대표이사', rq: { ref: refs.rq, ver: 2, value: RQ_VAL, md: RQ_MD, card: RQ_CARD, title: RQ_CARD.title } },
  }), 'flow create');
  const put = async (id: string, key: string, caller: string, data: Record<string, unknown>) =>
    ok(await request.put(`/api/storyboard/v1/flows/${id}/stages/${key}`, { headers: internalHeaders(caller), data }), `stage ${key}`);
  await put(main.id, 'dss', 'dss', { ref: refs.dss, ver: 1, value: DSS_VAL, md: DSS_MD, card: DSS_CARD, title: DSS_CARD.title });
  await put(main.id, 'mi', 'mi', { ref: refs.mi, ver: 1, value: { counts: { found: 11, kept: 11 } }, md: MI_MD, card: MI_CARD, title: MI_CARD.title });
  const br = await ok(await request.post(`/api/storyboard/v1/flows/${main.id}:branch`, { data: { stage: 'mi' } }), 'branch');
  await put(br.id, 'mi', 'mi', { ref: refs.mi2, ver: 1, value: { counts: { found: 9, kept: 9 } }, md: '- 담은 정보 9 · 리테일 테넌트 관점',
    card: { ...MI_CARD, title: '리테일 테넌트 관점', line: '담은 정보 9 · 리테일 테넌트 관점' }, title: '리테일 테넌트 관점' });
  // 보드 StrategyPopup BASE — Key message + 받쳐 줄 메시지 2
  const doc = await ok(await request.patch(`/api/storyboard/v1/flows/${main.id}`, { data: { key_message: KM, key_pillars: [
    { text: '사용자를 먼저 알아보는 공간', evidence: [`${refs.rq} 대표이사 1`, `${refs.dss} 로비`] },
    { text: '운영비를 줄이는 오피스', evidence: [`${refs.rq} 개발사업팀장 2`, `${refs.dss} b.IoT`] },
  ] } }), 'key message');
  return { id: main.id as string, branch: br.id as string, branchName: br.name as string, refs, doc };
}

async function backendDown(request: APIRequestContext) {
  const r = await request.get('/api/storyboard/v1/info').catch(() => null);
  return !r || !r.ok() ? 'storyboard 서비스가 꺼져 있어요(make dev-bg SERVICE=storyboard)' : null;
}

async function settle(page: Page) {
  await page.mouse.move(10, 890);
  await page.waitForTimeout(200);
}

test('SB0 · SB1 — 목록 · 진행 8칸 · 보기 팝업 · json · 전략 수립 AI 후보 · 요약본 수정 · 만들기 · 분기', async ({ page, request }) => {
  const down = await backendDown(request);
  test.skip(!!down, down ?? '');
  await page.setViewportSize({ width: 1440, height: 900 });
  const sb = await seed(request);
  const { refs } = sb;

  // ── SB0 — 목록 · 어디까지 입력됐나(메인 바로 아래 분기) ──
  await page.goto('/storyboard');
  await expect(page.getByRole('heading', { name: '전략 수립 Storyboard', level: 1 })).toBeVisible();
  await expect(page.getByText('제안서 흐름 전체를 담는 context예요. 고객 요구사항을 저장하면 생기고, 콘텐츠의 복제본을 만들면 분기돼요.')).toBeVisible();
  const newBtn = page.getByRole('link', { name: '새 고객 요구사항으로 시작' });
  await expect(newBtn).toHaveAttribute('href', '/requirements/new');
  const row = page.locator(`.sbf-row[data-sb="${sb.id}"]`);
  const brow = page.locator(`.sbf-row[data-sb="${sb.branch}"]`);
  await expect(row).toBeVisible();
  await expect(row.locator('.sbf-nametxt b')).toHaveText(NAME);
  await expect(row.locator('.sbf-nametxt small')).toHaveText(`${sb.id} · E 자산운용`);
  await expect(row.locator('.sbf-stage')).toHaveText('DSS + MI');
  await expect(row.locator('.sbf-km')).toHaveText(KM);
  await expect(row.locator('.sbf-when')).toHaveText(/^오늘 \d\d:\d\d$/);
  await expect(row.locator('.sbf-dot--on')).toHaveCount(3);
  await expect(brow.locator('.sbf-nametxt b')).toHaveText(`${NAME} · 분기 B`);
  await expect(brow.locator('.sbf-nametxt small')).toHaveText(`${sb.branch} · E 자산운용 · ${sb.id} · MI에서 분기`);
  await expect(brow.locator('.sbf-km')).toHaveText('아직 없음');   // 분기는 Key message 를 새로 세운다(보드 SB0)
  const rows = page.locator('.sbf-row');
  const ids = await rows.evaluateAll((els) => els.map((e) => e.getAttribute('data-sb')));
  expect(ids.indexOf(sb.branch)).toBe(ids.indexOf(sb.id) + 1);
  await expect(page.locator('.sbf-legend')).toHaveText('입력됨아직순서 · 요구사항 → DSS → MI · 경쟁사 · VP · Spec · 시나리오 → 제안서');
  // 보드 SB0: 본문 1100(1180 − 40×2) · 칸 minmax(0,1fr) 480 | 300 | 120 | 110(간격 16 · 안쪽 20) · 머리 42 · 줄 72 · 칸 22×14(간격 3 · 3번째 · 8번째 앞 +5) · 버튼 44
  expect(await w(page.locator('.sbf-table'))).toBe(1100);
  const th = page.locator('.sbf-th > span');
  expect([await w(th.nth(0)), await w(th.nth(1)), await w(th.nth(2)), await w(th.nth(3))]).toEqual([480, 300, 120, 110]);
  expect(await h(page.locator('.sbf-th'))).toBe(42);
  expect(await h(row)).toBe(72);
  expect(await h(newBtn)).toBe(44);
  const dots = row.locator('.sbf-dot');
  expect([await w(dots.first()), await h(dots.first())]).toEqual([22, 14]);
  expect(await x(dots.nth(1)) - await x(dots.nth(0))).toBe(25);
  expect(await x(dots.nth(2)) - await x(dots.nth(1))).toBe(30);
  await settle(page);
  await shot(page, 'SB0-new');

  // ── SB1 — 상세 ──
  await row.click();
  await expect(page).toHaveURL(new RegExp(`/storyboard/flow/${sb.id}$`));
  await expect(page.getByRole('heading', { name: NAME, level: 1 })).toBeVisible();
  await expect(page.locator('.sbf-badge')).toHaveText('main');
  await expect(page.locator('.sbf-headsub')).toHaveText(`${sb.id} · E 자산운용`);
  await expect(page.locator('.sbf-brbtn')).toHaveText('분기 1');
  await expect(page.locator('.sbf-auto')).toHaveText(/^요약본 자동 갱신 · 오늘 \d\d:\d\d$/);
  const cells = page.locator('.sbf-track .sbf-cell');
  await expect(cells).toHaveText([`요구사항${refs.rq} v2`, `DSS${refs.dss} v1`, `MI${refs.mi} v1`, '경쟁사+ 만들기', 'VP+ 만들기', 'Spec+ 만들기', '시나리오+ 만들기', '제안서후속 작업']);
  await expect(page.locator('.sbf-track a.sbf-cell[data-key="ca"]')).toHaveAttribute('href', `/competitor/new?sb=${sb.id}&auto=1`);
  await expect(page.locator('.sbf-track a.sbf-cell[data-key="ppt"]')).toHaveAttribute('href', `/proposal/new?sb=${sb.id}`);
  await expect(page.getByTestId('sb-key-message')).toContainText(`Key message${KM}`);
  await expect(page.locator('.sbf-conthead')).toHaveText('연결된 콘텐츠종류마다 하나씩');
  const crow = (k: string) => page.locator(`.sbf-crow[data-key="${k}"]`);
  await expect(crow('rq')).toHaveText(`고객 요구사항${refs.rq} v2 · 키맨 3 · 요구 12 · 확인 필요 4${wa(sb.branch)} 공유보기`);
  await expect(crow('dss')).toHaveText(`DSS${refs.dss} v1 · 오피스 · 공간 7 · 제품 12 · 솔루션 3${wa(sb.branch)} 공유보기`);
  await expect(crow('mi')).toHaveText(`MI${refs.mi} v1 · 담은 정보 11 · 출처 11보기`);
  const make: Record<string, [string, string]> = { ca: ['경쟁사 분석', 'competitor'], vp: ['Value Proposition', 'vp'], sp: ['Spec 시트', 'spec'], sc: ['공간 시나리오', 'scenario'] };
  for (const [k, [label, base]] of Object.entries(make)) {
    await expect(crow(k)).toHaveText(`${label}아직 없음 · 만들면 이 Storyboard를 가져가요만들기`);
    await expect(crow(k).getByRole('link', { name: `${label} 만들기` })).toHaveAttribute('href', `/${base}/new?sb=${sb.id}&auto=1`);
  }
  const md = page.getByTestId('sb-summary-md');
  const mdText = [
    `# ${NAME} — Storyboard 요약`, '고객: E 자산운용 · 최종 제안대상: 대표이사 · main', '',
    '## Key message', KM, '- 사용자를 먼저 알아보는 공간', '- 운영비를 줄이는 오피스', '',
    `## 1. 고객 요구사항 · ${refs.rq} v2`, ...RQ_MD.split('\n'), '',
    `## 2. DSS · ${refs.dss} v1`, ...DSS_MD.split('\n'), '',
    `## 3. Market Intelligence · ${refs.mi} v1`, '- 담은 정보 11 (시장 4 · 고객사 4 · 사용자 3)', '',
    '## 남은 것', '- 경쟁사 · VP · Spec · 공간 시나리오 → 제안서',
  ].join('\n');
  await expect(md).toHaveText(mdText);
  await expect(page.locator('.sbf-sidefoot')).toHaveText('콘텐츠가 저장될 때마다 다시 써져요 · 직접 고친 부분은 표시해 유지');
  await expect(page.locator('.sbf-follow')).toHaveText('후속 작업PPT 제작 · B2B 제안서이 Storyboard의 요약본 · 연결된 콘텐츠로 제안서를 만들어요');
  await expect(page.locator('.sbf-follow')).toHaveAttribute('href', `/proposal/new?sb=${sb.id}`);
  // 보드 SB1: 본문 1100 · 진행 8칸(간격 6 · 3번째 · 8번째 앞 +10 → 129.75) × 56 · 왼쪽 1fr 614 | 오른쪽 470(간격 16) · Key message 버튼 36 ·
  // 연결된 콘텐츠 머리 40+1 · 줄 50+1 · 이름 120 · 보기 · 만들기 30 · 탭 32 · 요약본 머리 46+1 · 바닥 38+1 · 후속 작업 64
  expect(await w(page.locator('.sbf-track'))).toBe(1100);
  // flex: 1 1 0 · border-box — 점선 테두리(1px)가 있는 빈 칸이 2px 넓다(보드도 같은 규칙): 입력됨 128.5 · 빈 칸 130.5
  const raw = async (l: Locator) => (await l.boundingBox())!;
  expect([(await raw(cells.nth(0))).width, (await raw(cells.nth(3))).width, await h(cells.first())]).toEqual([128.5, 130.5, 56]);
  expect((await raw(cells.nth(2))).x - (await raw(cells.nth(1))).x).toBe(128.5 + 6 + 10);
  expect([await w(page.locator('.sbf-left')), await w(page.locator('.sbf-side'))]).toEqual([614, 470]);
  expect(await h(page.getByTestId('sb-key-message').getByRole('button', { name: '전략 수립' }))).toBe(36);
  expect(await h(page.locator('.sbf-conthead'))).toBe(41);
  expect(await h(crow('rq'))).toBe(51);
  expect(await w(crow('rq').locator('.sbf-clabel'))).toBe(120);
  expect([await h(crow('rq').locator('.sbf-cta')), await h(crow('ca').locator('.sbf-cta'))]).toEqual([30, 30]);
  expect(await h(page.getByRole('tab', { name: '요약본 · md' }))).toBe(32);
  expect([await h(page.locator('.sbf-sidehead')), await h(page.locator('.sbf-sidefoot'))]).toEqual([47, 39]);
  expect([await w(page.locator('.sbf-follow')), await h(page.locator('.sbf-follow'))]).toEqual([1100, 64]);
  const follow = await page.locator('.sbf-follow').boundingBox();
  expect(Math.round(follow!.y + follow!.height)).toBe(900 - 22);   // 화면 높이를 채운다(section 아래 패딩 22)
  await settle(page);
  await shot(page, 'SB1-new');

  // ── SB1_View — 보기 = ContentPopup(페이지 이동 없음) ──
  const url = page.url();
  await page.getByRole('button', { name: 'DSS 보기' }).click();
  const cp = page.getByRole('dialog');
  await expect(cp).toContainText('용산 오피스 공간별 제품');
  await expect(cp).toContainText(`공간별 제품 매칭 DSS${refs.dss} v1`);
  await expect(cp.getByRole('link', { name: '편집 화면에서 고치기' })).toHaveAttribute('href', `/dss/${refs.dss}`);
  expect([await w(cp), await h(cp)]).toEqual([820, 680]);
  expect(page.url()).toBe(url);
  await settle(page);
  await shot(page, 'SB1_View-new');
  await cp.getByRole('button', { name: '닫기' }).last().click();
  await expect(cp).toHaveCount(0);
  await page.locator('.sbf-track .sbf-cell[data-key="rq"]').click();   // 진행 칸도 같은 팝업
  await expect(page.getByRole('dialog')).toContainText(RQ_CARD.title);
  await page.keyboard.press('Escape');

  // ── SB1_Json — 전체 흐름 · json(접힌 배열) ──
  await page.getByRole('tab', { name: '전체 흐름 · json' }).click();
  const js = page.getByTestId('sb-flow-json');
  await expect(js).toContainText(`"id": "${sb.id}",`);
  await expect(js).toContainText(`"branches": ["${sb.branch}"],`);
  await expect(js).toContainText(`"rq": { "ref": "${refs.rq}", "ver": 2,`);
  await expect(js).toContainText('"keymen": [ … 3 ]');
  await expect(js).toContainText('"ca": null, "vp": null, "sp": null, "sc": null, "ppt": null');
  await expect(js).toContainText('"progress": "dss+1/5",');
  await expect(js).toContainText(`"summary": "storyboards/${sb.id}/summary.md",`);
  await expect(page.getByRole('button', { name: '요약본 수정' })).toHaveCount(0);
  await expect(page.locator('.sbf-sidefoot')).toHaveText('콘텐츠의 실제 값까지 이 JSON 하나에 담겨요 · […]는 접힌 배열');
  await settle(page);
  await shot(page, 'SB1_Json-new');
  await page.getByRole('tab', { name: '요약본 · md' }).click();

  // ── SB1_Strat — 전략 수립(Key message + 받쳐 줄 메시지 3) ──
  await page.getByTestId('sb-key-message').getByRole('button', { name: '전략 수립' }).click();
  const sp = page.getByRole('dialog', { name: '전략 수립 · Key message' });
  await expect(sp).toContainText(`${NAME} · 전략 수립`);
  await expect(sp.locator('.sbk-src')).toHaveText([`요구사항 ${refs.rq} v2`, `${refs.dss} v1`, `${refs.mi} v1`]);
  await expect(sp.getByLabel('한 줄 메시지')).toHaveValue(KM);
  await expect(sp.getByLabel('메시지 1')).toHaveValue('사용자를 먼저 알아보는 공간');
  await expect(sp.getByLabel('메시지 3')).toHaveValue('');
  await expect(sp.locator('.sbk-pill').first().locator('.sbk-ev')).toHaveText([`${refs.rq} 대표이사 1`, `${refs.dss} 로비`]);
  await expect(sp.locator('.sbk-foot')).toHaveText('저장하면 요약본의 Key message 섹션이 바로 바뀌어요취소저장');
  // 보드 StrategyPopup: 1100×700 · AI 버튼 38 · 근거 칩 26+2 · 한 줄 입력 46 · 메시지 입력 34 · 번호 22 · 버튼 42
  expect([await w(sp), await h(sp)]).toEqual([1100, 700]);
  expect(await h(sp.getByRole('button', { name: '연결된 콘텐츠로 수립' }))).toBe(38);
  expect(await h(sp.locator('.sbk-src').first())).toBe(28);
  expect(await h(sp.getByLabel('한 줄 메시지'))).toBe(46);
  expect(await h(sp.getByLabel('메시지 1'))).toBe(34);
  expect(await w(sp.locator('.sbk-n').first())).toBe(22);
  expect(await h(sp.getByRole('button', { name: '저장', exact: true }))).toBe(42);
  await settle(page);
  await shot(page, 'SB1_Strat-new');

  // ── SB1_StratAI — AI 후보 3안(점선) → 이 안 쓰기 → 저장해야 들어간다 ──
  await sp.getByRole('button', { name: '연결된 콘텐츠로 수립' }).click();
  const cands = sp.getByTestId('sb-km-cand');
  await expect(cands).toHaveCount(3);
  await expect(sp.getByRole('button', { name: '연결된 콘텐츠로 수립' })).toHaveCount(0);
  await expect(sp.locator('.sbk-asidebody > small')).toHaveText(new RegExp(`^${refs.rq} · ${refs.dss} · ${refs.mi}(을|를) 읽고 만들었어요$`));
  await expect(cands.locator('.sbk-candhead')).toHaveText(['A공간이 먼저 알아보는 오피스', 'BAI Ready 오피스의 새로운 모델', 'C일하는 방식이 보이는 오피스']);
  await expect(cands.first()).toContainText('· 로비에서 시작되는 AI Ready 경험· 하나의 플랫폼으로 모든 공간 관리· 용산 최초 사례로 임대 가치 제고');
  expect(await w(sp.locator('.sbk-aside'))).toBe(361);   // 보드 360 + 왼쪽 테두리 1
  expect(await h(sp.locator('.sbk-asidehead'))).toBe(63);
  expect(await h(cands.first().getByRole('button', { name: '이 안 쓰기' }))).toBe(30);
  await expect(cands.first()).toHaveCSS('border-top-style', 'dashed');
  await settle(page);
  await shot(page, 'SB1_StratAI-new');
  await cands.first().getByRole('button', { name: '이 안 쓰기' }).click();
  await expect(sp.getByLabel('한 줄 메시지')).toHaveValue('공간이 먼저 알아보는 오피스');
  await expect(sp.getByText('AI 후보에서 고름')).toBeVisible();
  await expect(cands.first().getByRole('button', { name: '쓰는 중' })).toBeVisible();
  await expect(cands.first()).toHaveCSS('border-top-style', 'solid');
  await expect(sp.getByLabel('메시지 3')).toHaveValue('용산 최초 사례로 임대 가치 제고');
  await expect(sp.locator('.sbk-pill').first().locator('.sbk-ev')).toHaveText([`${refs.rq} 대표이사`, `${refs.dss} 로비`]);
  await shot(page, 'SB1_StratAI-picked-new');
  // 아직 저장 전 — 요약본은 그대로
  await expect(md).toContainText(`## Key message\n${KM}`);
  await sp.getByRole('button', { name: '저장', exact: true }).click();
  await expect(sp).toHaveCount(0);
  await expect(page.getByTestId('sb-key-message')).toContainText('공간이 먼저 알아보는 오피스');
  await expect(md).toContainText('## Key message\n공간이 먼저 알아보는 오피스\n- 로비에서 시작되는 AI Ready 경험\n- 하나의 플랫폼으로 모든 공간 관리\n- 용산 최초 사례로 임대 가치 제고\n');
  const saved = await ok(await request.get(`/api/storyboard/v1/flows/${sb.id}`), 'flow');
  expect(saved.key_message.by).toBe('ai-accepted');
  expect(saved.flow_json.keyMessage).toBe('공간이 먼저 알아보는 오피스');

  // ── 요약본 수정 — 직접 고친 문장은 ✎ 로, 콘텐츠가 다시 저장돼도 남는다 ──
  await page.getByRole('button', { name: '요약본 수정' }).click();
  const ta = page.getByLabel('요약본 수정');
  await expect(page.getByRole('button', { name: '저장', exact: true })).toBeVisible();
  await expect(page.locator('.sbf-sidefoot')).toHaveText('직접 고친 문장은 콘텐츠가 바뀌어도 유지돼요');
  const cur = await ta.inputValue();
  await ta.fill(cur.replace(`## 2. DSS · ${refs.dss} v1\n`, `## 2. DSS · ${refs.dss} v1\n- 회의실 수량은 11월 실사 뒤 확정\n`));
  expect(await w(ta)).toBe(470 - 2 - 20);   // 보드: 바깥 여백 10 · 테두리 1.5 brand
  await settle(page);
  await shot(page, 'SB1_Edit-new');
  await page.getByRole('button', { name: '저장', exact: true }).click();
  await expect(md).toContainText('- 회의실 수량은 11월 실사 뒤 확정 ✎');
  await expect(page.getByRole('button', { name: '요약본 수정' })).toBeVisible();
  // 경쟁사 분석이 저장되면(콘텐츠 서비스 → 허브) 요약본을 다시 쓴다 — 사람 문장은 남는다
  await ok(await request.put(`/api/storyboard/v1/flows/${sb.id}/stages/ca`, { headers: internalHeaders('competitor'),
    data: { ref: `CA-${refs.rq.slice(3)}`, ver: 1, value: { counts: { competitors: 5 } }, md: '## 경쟁사 분석 · CA\n- 경쟁사 5 (직접 2 · AI 웹 탐색 3) · 비교 쌍 9',
      card: { title: '용산 오피스 경쟁사', facts: [], groups: [], line: '경쟁사 5 · 비교 쌍 9' } } }), 'ca stage');
  await page.reload();
  await expect(md).toContainText(`## 2. DSS · ${refs.dss} v1\n${DSS_MD}\n- 회의실 수량은 11월 실사 뒤 확정 ✎`);
  await expect(md).toContainText(`## 4. 경쟁사 분석 · CA-${refs.rq.slice(3)} v1\n- 경쟁사 5 (직접 2 · AI 웹 탐색 3) · 비교 쌍 9`);
  await expect(md).toContainText('## 남은 것\n- VP · Spec · 공간 시나리오 → 제안서');
  await expect(crow('ca')).toHaveText(`경쟁사 분석CA-${refs.rq.slice(3)} v1 · 경쟁사 5 · 비교 쌍 9보기`);
  await expect(cells.nth(3)).toHaveText(`경쟁사CA-${refs.rq.slice(3)} v1`);

  // ── 만들기 — Gate 를 건너뛰고 이 Storyboard 를 가져가 새로 만들기(CF-07) ──
  await crow('vp').getByRole('link', { name: 'Value Proposition 만들기' }).click();
  await expect(page).toHaveURL(new RegExp(`/vp/(new\\?sb=${sb.id}&auto=1|values/)`));
  // VP Gate(autoStart)가 이 Storyboard 로 바로 만들고 편집 화면으로 — 위 SB 바에 이 Storyboard
  await expect(page).toHaveURL(/\/vp\/values\/vmap_/, { timeout: 20_000 });
  await expect(page.locator('.wm-sbbar__chip').first()).toContainText(NAME);
  await page.goto(`/storyboard/flow/${sb.id}`);

  // ── 분기 — 「분기 1」 → 분기 Storyboard 요약 팝업(SBPopup) → 열기 ──
  await page.locator('.sbf-brbtn').click();
  const opt = page.getByRole('menuitem');
  await expect(opt).toHaveText(`${NAME} · 분기 B${sb.branch} · MI에서 분기 · ${refs.mi2} 리테일 테넌트 관점`);
  expect(await w(page.locator('.sbf-brpop'))).toBe(300);
  await settle(page);
  await shot(page, 'SB1_BranchMenu-new');
  await opt.click();
  const pop = page.getByRole('dialog').filter({ hasText: 'SUMMARY.MD' });   // 공용 SBPopup 은 머리 내용이 이름(aria-labelledby)
  await expect(pop).toContainText(`Storyboard · ${sb.branch}`);
  await expect(pop).toContainText(`E 자산운용 · ${sb.id} · MI에서 분기`);
  expect([await w(pop), await h(pop)]).toEqual([760, 660]);
  await settle(page);
  await shot(page, 'SBPopup-branch-new');
  await pop.getByRole('link', { name: 'Storyboard 열기' }).click();
  await expect(page).toHaveURL(new RegExp(`/storyboard/flow/${sb.branch}$`));
  await expect(page.locator('.sbf-badge')).toHaveText('분기 B');
  await expect(page.locator('.sbf-parent')).toHaveText(`${sb.id} · MI에서 분기`);
  await expect(crow('rq')).toContainText(`${wa(sb.id)} 공유`);
  await expect(crow('mi')).toHaveText(`MI${refs.mi2} v1 · 담은 정보 9 · 리테일 테넌트 관점보기`);
  await expect(crow('ca')).toContainText('아직 없음');   // 경쟁사는 메인에만
  await expect(page.getByTestId('sb-key-message')).toContainText('아직 없음');
  await expect(md).toContainText(`고객: E 자산운용 · 최종 제안대상: 대표이사 · 분기 B\n\n## 1. 고객 요구사항 · ${refs.rq} v2`);
  await settle(page);
  await shot(page, 'SB1_Branch-new');
  // 부모로 — 칩을 누르면 부모 요약
  await page.locator('.sbf-parent').click();
  await expect(page.getByRole('dialog').filter({ hasText: 'SUMMARY.MD' })).toContainText(`Storyboard · ${sb.id}`);
  await page.keyboard.press('Escape');

  // ── 1920 폭 — 본문 열은 1180 가운데(UI-W-01), 칸은 같은 px ──
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(`/storyboard/flow/${sb.id}`);
  await expect(page.getByTestId('sb-summary-md')).toBeVisible();
  expect([await w(page.locator('.sbf-track')), await w(page.locator('.sbf-left')), await w(page.locator('.sbf-side'))]).toEqual([1100, 614, 470]);
  const fb = (await page.locator('.sbf-follow').boundingBox())!;
  expect(Math.round(fb.y + fb.height)).toBe(1080 - 22);
  await page.goto('/storyboard');
  await expect(row).toBeVisible();
  expect(await w(page.locator('.sbf-table'))).toBe(1100);
});
