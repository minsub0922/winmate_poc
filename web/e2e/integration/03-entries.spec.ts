/**
 * 여정 3 — 기능 사이 진입 경로(쿼리 · 라우트)와 「새 제안서로 시작」 · 이미지 ↔ 시나리오 · 조감도 왕복(실제 스택, 흉내 없음).
 *
 *  정의서 → MI(RQ4 카드) · 경쟁사(CA1R ?rq=) · VP(Storyboard ?sb=) 를 화면으로 시작하고,
 *  각 기능의 「새 제안서로 시작」(MI4 · CA5 · VP4 · SP4 · IMG4 · BE6 · SC5 · SB4)이 연결 자료가 붙은 제안서 PR1 을 여는지,
 *  CA5 새 제안서는 유형을 고르면 Why Samsung 섹션이 그 분석으로 채워지는지(hof_ 접두사 겹침 — 분석 id 로 기능 판별),
 *  IMG4 「조감도 참조로」 · BE6 「시나리오 시작」 · 「Spec 시작」 · 제안서 「조감도 새로 만들기」 · SC4 「이미지 생성」 → IMG4 「공간 시나리오 장면으로」,
 *  MI4 · VP4 「공간 시나리오」(페르소나 · 가치가 SC 입력으로)를 본다.
 */
import { expect as baseExpect, test, type Page } from '@playwright/test';
import {
  api, backendDown, budget, cleanup, clickIfShown, composeProposal, ID, open, seedBirdseye, seedCa, seedImage, seedMi, seedRequirement, seedScenario,
  seedSpec, seedStoryboard, seedVp, shot, tag, until, waitJob,
} from './helpers';

const expect = baseExpect.configure({ timeout: 20_000 });
test.describe.configure({ mode: 'serial', timeout: 150_000 });
test.use({ actionTimeout: 30_000, navigationTimeout: 60_000 });

const T = tag();
const W: Record<string, string> = {};
const made = { pr: [] as string[], mi: [] as string[], ca: [] as string[], vp: [] as string[], sp: [] as string[], be: [] as string[], sc: [] as string[], img: [] as string[] };
let rq: { id: string; project_id: string | null } = { id: '', project_id: null };

test.beforeAll(async ({ request }) => {
  test.setTimeout(1_200_000);
  const down = await backendDown(request, ['requirements', 'storyboard', 'mi', 'competitor', 'vp', 'spec', 'image', 'birdseye', 'scenario', 'proposal']);
  test.skip(!!down, down ?? '');
  rq = await seedRequirement(request);
  W.sb = await seedStoryboard(request, rq.id, 'saved');
  W.mi = await seedMi(request, rq.id, W.sb); made.mi.push(W.mi);
  W.ca = await seedCa(request, rq.id); made.ca.push(W.ca);
  W.vp = await seedVp(request, W.sb, W.mi); made.vp.push(W.vp);
  W.sp = await seedSpec(request, rq); made.sp.push(W.sp);
  const im = await seedImage(request, rq.project_id);
  W.imgWork = im.work; W.img = im.image; W.imv = im.version; made.img.push(im.work);
  W.be = await seedBirdseye(request, `[IT3] 로비 조감도 ${T}`, rq.project_id); made.be.push(W.be);
  W.sc = await seedScenario(request, W.be, `[IT3] 로비 동선 ${T}`); made.sc.push(W.sc);
});

test.afterAll(async ({ request }) => { await cleanup(request, made); });

/** 「새 제안서로 시작」 류 → PR1 이 열리고 연결 자료가 붙었는지 */
async function expectNewProposal(page: Page, request: any, feature: string, refId: string | null) {
  await expect(page).toHaveURL(/\/proposal\/pr_[0-9A-HJKMNP-TV-Z]{26}\/customer$/, { timeout: 60_000 });
  const pid = page.url().match(ID('pr'))![0];
  made.pr.push(pid);
  await expect(page.getByTestId('pr1')).toBeVisible();
  const links = await api(request, 'proposal', 'GET', `/proposals/${pid}/links`);
  const ln = links.links.find((l: any) => l.feature === feature);
  expect(ln, `${feature} 연결 자료`).toBeTruthy();
  if (refId) expect(ln.ref_id).toBe(refId);
  return pid;
}

test('RQ4 「Market Intelligence」 카드 → MI1(정의서 · 사용 링크) → 분석 설계 → 결과 · MI4 「새 제안서로 시작」 → PR1(MI 연결)', async ({ page, request }) => {
  budget(240_000);
  await open(page, `/requirements/${rq.id}/saved?v=1`);
  await page.locator('.rq-nextcard', { hasText: 'Market Intelligence' }).click();
  await expect(page).toHaveURL(/\/mi\/mi_[0-9A-HJKMNP-TV-Z]{26}\/input$/, { timeout: 60_000 });
  const mi = page.url().match(ID('mi'))![0];
  made.mi.push(mi);
  const a = await api(request, 'mi', 'GET', `/analyses/${mi}`);
  expect(a.links.requirements_id).toBe(rq.id);
  expect(a.requirements.length).toBeGreaterThan(5);
  await page.getByTestId('mi1-next').click();
  await expect(page).toHaveURL(new RegExp(`/mi/${mi}/design`), { timeout: 60_000 });
  const d = await until(() => api(request, 'mi', 'GET', `/analyses/${mi}/design`), (x: any) => ['done', 'ask', 'failed'].includes(x.status), 90_000, 'MI 설계');
  expect(d.status).toBe('done');
  await api(request, 'mi', 'POST', `/analyses/${mi}/runs`, { mode: 'full' });
  await until(() => api(request, 'mi', 'GET', `/analyses/${mi}`), (x: any) => ['done', 'upd'].includes(x.status), 180_000, 'MI 분석');
  await open(page, `/mi/${mi}/result`);
  await expect(page.locator('#wm-main')).toContainText('분석이 끝났습니다', { timeout: 30_000 });
  await open(page, `/mi/${mi}/export`);
  await page.getByRole('link', { name: '새 제안서로 시작' }).click();
  await expectNewProposal(page, request, 'mi', mi);
  await shot(page, 'J3-mi4-new-proposal');
});

test('CA1R(?input=requirements&rq=) → 경쟁사 찾기 · 분석 → CA5 「새 제안서로 시작」 → PR1 → 유형 고르면 Why Samsung 이 그 분석으로', async ({ page, request }) => {
  budget(300_000);
  await open(page, `/competitor/new?input=requirements&rq=${rq.id}`);
  const radios = page.getByRole('radiogroup', { name: '요구사항 정의서' });
  await expect(radios.getByRole('radio', { checked: true })).toContainText('E 자산운용', { timeout: 30_000 });
  await page.getByRole('button', { name: '경쟁사 찾기' }).click();
  await expect(page).toHaveURL(/\/competitor\/ca_[0-9A-HJKMNP-TV-Z]{26}\//, { timeout: 60_000 });
  const ca = page.url().match(ID('ca'))![0];
  made.ca.push(ca);
  const c = await until(() => api(request, 'competitor', 'GET', `/analyses/${ca}`), (x: any) => ['confirming', 'ask', 'failed'].includes(x.status), 90_000, '경쟁사 찾기');
  expect(c.status).toBe('confirming');
  expect(c.requirements_id ?? c.requirement_ref ?? rq.id).toBe(rq.id);
  const cands = await api(request, 'competitor', 'GET', `/analyses/${ca}/candidates`);
  if (!cands.items.some((x: any) => x.on)) for (const x of cands.items.slice(0, 2)) await api(request, 'competitor', 'PATCH', `/analyses/${ca}/candidates/${x.id}`, { on: true });
  await api(request, 'competitor', 'POST', `/analyses/${ca}/runs`, { mode: 'full' });
  await until(() => api(request, 'competitor', 'GET', `/analyses/${ca}`), (x: any) => ['done', 'upd', 'stopped'].includes(x.status), 180_000, '경쟁사 분석');
  const links = await api(request, 'requirements', 'GET', `/requirements/${rq.id}/links`);
  expect(links.items.some((l: any) => l.service === 'competitor' && l.ref_id === ca)).toBeTruthy();

  await open(page, `/competitor/${ca}/send`);
  await page.getByRole('button', { name: /제안서 Why Samsung · 경쟁 비교 시트로/ }).click();
  await clickIfShown(page, page.getByRole('button', { name: '익명으로 보내기' }), page.getByRole('list', { name: '최근 제안서' }));
  await page.getByRole('list', { name: '최근 제안서' }).getByRole('listitem').filter({ hasText: '새 제안서로 시작' }).click();
  const pid = await expectNewProposal(page, request, 'competitor', ca);
  const h = await api(request, 'competitor', 'GET', `/analyses/${ca}/handoffs`);
  expect((h.items ?? []).some((x: any) => x.target === 'proposal_why')).toBeTruthy();
  await composeProposal(request, pid, 'standard');
  const why = await until(() => api(request, 'proposal', 'GET', `/proposals/${pid}/sections/why`),
    (s: any) => s.status !== 'filling' && s.sources.some((x: any) => x.feature === 'competitor'), 60_000, 'Why Samsung 연결');
  expect(why.sources.find((x: any) => x.feature === 'competitor').label).toContain('경쟁사');
  await shot(page, 'J3-ca5-new-proposal');
});

test('SB4 → VP(?sb=) 재료 · 구조 · 생성 → VP4 「새 제안서로」 → ?handoff=vho_ → PR1(VP 연결)', async ({ page, request }) => {
  budget(300_000);
  await open(page, `/vp/new?sb=${W.sb}`);
  await expect(page).toHaveURL(/\/vp\/vp_[0-9A-HJKMNP-TV-Z]{26}\//, { timeout: 60_000 });
  const vp = page.url().match(ID('vp'))![0];
  made.vp.push(vp);
  // 재료 잡 → (확인 · 되묻기) → 가치 구조
  await page.waitForURL(/\/(questions|materials\/review|structure)$/, { timeout: 120_000 });
  for (let i = 0; i < 3 && !/\/structure$/.test(page.url()); i++) {
    if (/\/materials\/review$/.test(page.url())) await page.getByRole('button', { name: '가치 구조로' }).click();
    else await page.getByRole('button', { name: '이대로 진행' }).click();
    await page.waitForURL(/\/(questions|materials\/review|structure)$/, { timeout: 90_000 });
  }
  const d0 = await api(request, 'vp', 'GET', `/vps/${vp}`);
  expect(d0.sources.some((s: any) => s.kind === 'storyboard' && s.ref_id === W.sb && s.connected)).toBeTruthy();
  await page.getByRole('button', { name: /장 만들기/ }).click();
  await page.waitForURL(new RegExp(`/vp/${vp}/result$`), { timeout: 180_000 });
  await open(page, `/vp/${vp}/export`);
  await page.getByRole('button', { name: '새 제안서로' }).click();
  await expect(page).toHaveURL(/\/proposal\/pr_[0-9A-HJKMNP-TV-Z]{26}\/customer$/, { timeout: 60_000 });
  const pid = await expectNewProposal(page, request, 'vp', vp);
  await composeProposal(request, pid, 'standard');
  const sec = await until(() => api(request, 'proposal', 'GET', `/proposals/${pid}/sections/vp`), (s: any) => s.status !== 'filling'
    && s.sources.some((x: any) => x.feature === 'vp'), 60_000, 'VP 섹션');
  expect(sec.sources.find((x: any) => x.feature === 'vp').label).toContain('가치 제안');
});

test('SP4 「새 제안서로 시작」 → ?handoff=sho_ → PR1(Spec 연결) · BE6 「Spec 시작」 → Spec 시트가 조감도 출처 · 제품을 받는다', async ({ page, request }) => {
  budget(150_000);
  await open(page, `/spec/${W.sp}/export`);
  await page.getByRole('button', { name: /새 제안서로 시작/ }).first().click();
  await expectNewProposal(page, request, 'spec', W.sp);
  // BE6 → Spec
  await open(page, `/birdseye/${W.be}/export`);
  await page.getByTestId('be6-spec').click();
  await expect(page).toHaveURL(/\/spec\/sp_[0-9A-HJKMNP-TV-Z]{26}\//, { timeout: 60_000 });
  const sp = page.url().match(ID('sp'))![0];
  made.sp.push(sp);
  const s = await api(request, 'spec', 'GET', `/sheets/${sp}`);
  expect(s.products.length).toBeGreaterThan(0);
  expect(JSON.stringify(s.origin ?? s.agent ?? {})).toContain('birdseye');
});

test('IMG4 「새 제안서로 시작」(이미지 연결 · 프로젝트 잇기) · 「조감도 참조로」 → BE1 참조 이미지 → 조감도가 이미지 사용 등록', async ({ page, request }) => {
  budget(150_000);
  await open(page, `/image/w/${W.imgWork}/export/${W.img}`);
  await page.getByRole('link', { name: '새 제안서로 시작' }).first().click();
  const pid = await expectNewProposal(page, request, 'image', W.img);
  const p = await api(request, 'proposal', 'GET', `/proposals/${pid}`);
  expect(p.project_id).toBe(rq.project_id);

  await open(page, `/image/w/${W.imgWork}/export/${W.img}`);
  await page.getByRole('link', { name: '조감도 참조로' }).click();
  await expect(page).toHaveURL(/\/birdseye\/new\?ref_version=imv_/);
  await expect(page.getByTestId('be1-ref')).toContainText('참조 이미지');
  await page.locator('#be-space').fill('용산 오피스 라운지. 약 40평, 층고 3.2m.');
  await page.getByTestId('be1-next').click();
  await expect(page).toHaveURL(/\/birdseye\/be_[0-9A-HJKMNP-TV-Z]{26}\//, { timeout: 60_000 });
  const be = page.url().match(ID('be'))![0];
  made.be.push(be);
  const b = await api(request, 'birdseye', 'GET', `/birdseyes/${be}`);
  expect(b.reference_image?.version_id).toBe(W.imv);
  const info = await api(request, 'image', 'GET', `/images/${W.img}/info`);
  expect(info.rows.find((r: any) => r.k === '사용 이력')?.v ?? '').toMatch(/조감도 \d+건/);
});

test('BE6 「새 제안서로 시작」(조감도 연결) · 「시나리오 시작」 → SC1B → 조감도에서 이어 만든 시나리오(BE 쓰인 곳)', async ({ page, request }) => {
  budget(180_000);
  await open(page, `/birdseye/${W.be}/export`);
  await page.getByRole('link', { name: '새 제안서로 시작' }).click();
  await expectNewProposal(page, request, 'birdseye', W.be);

  await open(page, `/birdseye/${W.be}/export`);
  await page.getByTestId('be6-scenario').click();
  await expect(page).toHaveURL(new RegExp(`/scenario/new/birdseye\\?birdseye=${W.be}`));
  await shot(page, 'J3-sc1b-from-be6');
  await page.getByTestId('sc1b-start').click();
  await expect(page).toHaveURL(/\/scenario\/sc_[0-9A-HJKMNP-TV-Z]{26}\//, { timeout: 60_000 });
  const sc = page.url().match(ID('sc'))![0];
  made.sc.push(sc);
  const s = await until(() => api(request, 'scenario', 'GET', `/scenarios/${sc}`), (x: any) => !x.active_job, 90_000, '시나리오 골격');
  expect(s.birdseye_link?.birdseye_id).toBe(W.be);
  expect(s.project_id).toBe(rq.project_id);
  const list = await api(request, 'birdseye', 'GET', '/birdseyes?limit=20');
  expect((list.items.find((x: any) => x.id === W.be)?.usages ?? []).some((u: any) => u.service === 'scenario' && u.ref === sc)).toBeTruthy();
});

test('SC4 「이미지 생성」 → IMG2(장면 미리 채움) → 생성 → IMG4 「공간 시나리오 장면으로」 → SC 장면에 붙음 · SC5 「새 제안서로 시작」', async ({ page, request }) => {
  budget(300_000);
  // 장면 이미지가 이미 있으면(장면 이미지 모두 생성) SC4E 「이미지 생성에서 다시 만들기」, 없으면 SC4 카드 「이미지 생성」
  const scenes0 = await api(request, 'scenario', 'GET', `/scenarios/${W.sc}/scenes`);
  const target = scenes0.items[1] ?? scenes0.items[0];
  const before = target.image?.version_id ?? null;
  await open(page, `/scenario/${W.sc}/scenes/${target.id}`);
  await page.getByTestId('sc4e-make-image').click();
  await expect(page).toHaveURL(/\/image\/(w\/imw_[0-9A-Z]+\/conditions|new\?)/, { timeout: 60_000 });
  const work = page.url().match(/imw_[0-9A-HJKMNP-TV-Z]{26}/)?.[0];
  if (work) made.img.push(work);
  if (!/\/conditions/.test(page.url())) await page.getByRole('button', { name: '상세 조건 입력' }).click();
  await expect(page).toHaveURL(/\/conditions$/);
  await page.getByRole('button', { name: '2장', exact: true }).click();
  await page.getByRole('button', { name: /이미지 2장 생성/ }).click();
  await expect(page.getByRole('button', { name: '결과 보기' })).toBeEnabled({ timeout: 120_000 });
  await page.getByRole('button', { name: '결과 보기' }).click();
  await page.getByRole('button', { name: /제안서에 넣기/ }).click();
  await expect(page).toHaveURL(/\/export\//);
  await page.getByRole('button', { name: '공간 시나리오 장면으로' }).click();
  await expect(page).toHaveURL(new RegExp(`/scenario/${W.sc}/scenes/${target.id}`), { timeout: 60_000 });
  const sc = await api(request, 'scenario', 'GET', `/scenarios/${W.sc}/scenes`);
  const after = sc.items.find((x: any) => x.id === target.id)?.image;
  expect(after?.version_id, '장면 이미지가 IMG4 에서 고른 시안으로 바뀐다').toBeTruthy();
  expect(after.version_id).not.toBe(before);
  await shot(page, 'J3-sc4e-image-from-img4');

  await open(page, `/scenario/${W.sc}/send`);
  await page.getByTestId('sc5-new-proposal').click();
  await expectNewProposal(page, request, 'scenario', W.sc);
});

test('SB4 「B2B 제안서」 → PR1(Storyboard · 정의서) · 섹션 「조감도 새로 만들기」 → BE1 ?return_to= 제안서 섹션', async ({ page, request }) => {
  budget(150_000);
  await open(page, `/storyboard/${W.sb}/saved`);
  await page.getByTestId('handoff-proposal').click();
  const pid = await expectNewProposal(page, request, 'storyboard', W.sb);
  await expect(page.getByLabel('고객사')).toHaveValue('E 자산운용');
  const p = await api(request, 'proposal', 'GET', `/proposals/${pid}`);
  expect(p.rq_ref?.rq_id).toBe(rq.id);
  await composeProposal(request, pid, 'standard');
  await open(page, `/proposal/${pid}/sections/birdseye`);
  await expect(page.getByTestId('pr-section')).toBeVisible({ timeout: 30_000 });
  await page.getByRole('button', { name: '조감도 새로 만들기' }).first().click();
  await expect(page).toHaveURL(/\/birdseye\/new\?return_to=/, { timeout: 30_000 });
  await page.locator('#be-space').fill('용산 오피스 회의실. 약 15평.');
  await page.getByTestId('be1-next').click();
  await expect(page).toHaveURL(/\/birdseye\/be_[0-9A-HJKMNP-TV-Z]{26}\//, { timeout: 60_000 });
  const be = page.url().match(ID('be'))![0];
  made.be.push(be);
  const b = await api(request, 'birdseye', 'GET', `/birdseyes/${be}`);
  expect(b.origin?.return_to ?? '').toContain(`/proposal/${pid}/sections/birdseye`);
});

test('MI4 「공간 시나리오」 → SC1(페르소나 → 등장인물 · 고객 · 프로젝트) · VP4 「공간 시나리오」 → SC1(가치 → 입력 줄)', async ({ page, request }) => {
  budget(150_000);
  // MI4 → `/scenario/new?mi=&personas=` — 페르소나가 등장인물 칩 · 「[인물] …」 줄로, 고객 · 프로젝트를 잇는다
  await open(page, `/mi/${W.mi}/export`);
  await page.locator('#wm-main').getByRole('link', { name: /공간 시나리오/ }).first().click();
  await expect(page).toHaveURL(new RegExp(`/scenario/new\\?mi=${W.mi}`), { timeout: 30_000 });
  await expect(page.getByTestId('sc1-seed')).toContainText('페르소나', { timeout: 30_000 });
  await page.getByTestId('sc1-next').click();
  await expect(page).toHaveURL(/\/scenario\/sc_[0-9A-HJKMNP-TV-Z]{26}\/input/, { timeout: 30_000 });
  const s1 = page.url().match(ID('sc'))![0];
  made.sc.push(s1);
  const mi = await api(request, 'mi', 'GET', `/analyses/${W.mi}`);
  const a = await api(request, 'scenario', 'GET', `/scenarios/${s1}`);
  expect(a.customer_name).toBe('E 자산운용');
  if (mi.project_id) expect(a.project_id).toBe(mi.project_id);
  expect(a.raw_text).toContain('[인물] ');
  expect(a.characters.length).toBeGreaterThan(0);
  await expect(page.locator('#wm-main')).toContainText(a.characters[0]);
  await shot(page, 'J3-sc-from-mi4');

  // VP4 → `/scenario/new?from=vp:` — 이해관계자별 가치 · 과제 · 제품이 입력 줄로
  await open(page, `/vp/${W.vp}/export`);
  await page.locator('#wm-main').getByRole('link', { name: /공간 시나리오/ }).first().click();
  await expect(page).toHaveURL(new RegExp(`/scenario/new\\?from=vp:${W.vp}`), { timeout: 30_000 });
  await expect(page.getByTestId('sc1-seed')).toContainText('Value Proposition', { timeout: 30_000 });
  await page.getByTestId('sc1-next').click();
  await expect(page).toHaveURL(/\/scenario\/sc_[0-9A-HJKMNP-TV-Z]{26}\/input/, { timeout: 30_000 });
  const s2 = page.url().match(ID('sc'))![0];
  made.sc.push(s2);
  const b = await api(request, 'scenario', 'GET', `/scenarios/${s2}`);
  expect(b.customer_name).toBe('E 자산운용');
  expect(b.raw_text).toMatch(/\[가치/);
  await shot(page, 'J3-sc-from-vp4');
});
