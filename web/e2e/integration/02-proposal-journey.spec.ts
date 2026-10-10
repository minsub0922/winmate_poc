/**
 * 여정 2 — 정의서 하나로 만든 모든 작업을 B2B 제안서 한 부로 모은다(실제 스택, page.route 흉내 없음).
 *
 *  준비(API): 정의서 v1 → Storyboard(저장) → MI(정의서 + Storyboard) → 경쟁사(정의서) → VP(Storyboard + MI) → Spec(정의서 연결)
 *             → 이미지(제품 참조 QM55C) → 조감도(공간 → 제품 → 배치 → 렌더 → 존) → 시나리오(조감도 존 → 생성 → 장면 이미지)
 *  화면: RQ6 「쓰는 곳 · 제안서」 → PR1 · PR2 · PR3 → 각 기능의 「제안서로 보내기」(MI4 · CA5 · VP4 · SP4 · IMG4 · BE6 · SC5)
 *        → 제안서 안 끌어 놓기(사이드바 MI → Why Samsung) → 딸깍 → PR6 생성 → PR7 PPTX 내려받기 → 쓰는 곳 · 사용 표시 → 지우면 사용 표시 거둠
 */
import { expect as baseExpect, test, type Page } from '@playwright/test';
import {
  api, backendDown, budget, cleanup, clickIfShown, composeProposal, downloadName, ID, open, seedBirdseye, seedCa, seedImage, seedMi, seedRequirement,
  seedScenario, seedSpec, seedStoryboard, seedVp, shot, tag, until, waitJob,
} from './helpers';

const expect = baseExpect.configure({ timeout: 20_000 });
test.describe.configure({ mode: 'serial', timeout: 150_000 });
test.use({ actionTimeout: 30_000, navigationTimeout: 60_000 });

const T = tag();
const TITLE = `[IT] 용산 AI Ready 오피스 제안 ${T}`;
const W: Record<string, string> = {};   // 이 여정이 만든 작업 id
let rq: { id: string; project_id: string | null } = { id: '', project_id: null };
let pid = '';

test.beforeAll(async ({ request }) => {
  test.setTimeout(1_200_000);
  const down = await backendDown(request, ['requirements', 'storyboard', 'mi', 'competitor', 'vp', 'spec', 'image', 'birdseye', 'scenario', 'proposal']);
  test.skip(!!down, down ?? '');
  rq = await seedRequirement(request);
  W.sb = await seedStoryboard(request, rq.id, 'saved');
  W.mi = await seedMi(request, rq.id, W.sb);
  W.ca = await seedCa(request, rq.id);
  W.vp = await seedVp(request, W.sb, W.mi);
  W.sp = await seedSpec(request, rq);
  const im = await seedImage(request, rq.project_id);
  W.imgWork = im.work; W.img = im.image; W.imv = im.version;
  W.be = await seedBirdseye(request, `[IT] 용산 로비 조감도 ${T}`, rq.project_id);
  W.sc = await seedScenario(request, W.be, `[IT] 로비 방문객 동선 ${T}`);
});

test.afterAll(async ({ request }) => {
  await cleanup(request, { pr: [pid], mi: [W.mi], ca: [W.ca], vp: [W.vp], sp: [W.sp], img: [W.imgWork], be: [W.be], sc: [W.sc] });
});

const sectionUrl = (key: string) => new RegExp(`/proposal/${pid}/sections/${key}(\\?|$)`);
async function lastImport(request: any, featureKey: string) {
  const links = await api(request, 'proposal', 'GET', `/proposals/${pid}/links`);
  return (links.links ?? []).filter((l: any) => l.feature === featureKey && l.status !== 'removed');
}
type SheetRow = { id: string; title: string; role: string; status: string };
/** 섹션 시트(섹션이 「작성 중」이면 빈 목록 — 반입 잡이 채우기를 끝낸 뒤만 본다) */
async function sheetsOf(request: any, key: string): Promise<SheetRow[]> {
  const s = await api(request, 'proposal', 'GET', `/proposals/${pid}/sections/${key}`);
  return s.status === 'filling' ? [] : s.sheets as SheetRow[];
}
const filled = (s: SheetRow[], roles: string[]) => roles.every((r) => s.some((x) => x.role === r && ['ready', 'updated'].includes(x.status)));

test('RQ6 「쓰는 곳 · 제안서」 → PR1(고객 미리 채움 · 프로젝트 잇기) → 표준 제안서 · 시트 구성 → 첫 섹션', async ({ page, request }) => {
  budget(120_000);
  await open(page, `/requirements/${rq.id}`);
  await page.locator('.rq-usechip', { hasText: '제안서' }).click();
  await expect(page).toHaveURL(/\/proposal\/pr_[0-9A-HJKMNP-TV-Z]{26}\/customer$/, { timeout: 60_000 });
  pid = page.url().match(ID('pr'))![0];
  await expect(page.getByTestId('pr1')).toBeVisible();
  await expect(page.getByLabel('고객사')).toHaveValue('E 자산운용');
  await page.getByLabel('프로젝트명').fill(TITLE);
  await expect.poll(async () => (await api(request, 'proposal', 'GET', `/proposals/${pid}`)).title, { timeout: 15_000 }).toBe(TITLE);
  const p = await api(request, 'proposal', 'GET', `/proposals/${pid}`);
  expect(p.rq_ref?.rq_id).toBe(rq.id);
  expect(p.project_id, '정의서 프로젝트를 잇는다').toBe(rq.project_id);
  await shot(page, 'J2-pr1-from-rq');

  await page.getByTestId('pr1-next').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${pid}/type$`));
  await page.getByTestId('pr2-type-standard').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${pid}/compose`));
  await expect(page.getByTestId('pr3-list')).toBeVisible();
  await page.getByTestId('pr3-start').click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${pid}/(industry|sections/)`), { timeout: 30_000 });
  if (page.url().includes('/industry')) await page.getByTestId('pr3i-apply').click();
  await expect(page).toHaveURL(sectionUrl('mi'), { timeout: 30_000 });
  await expect(page.getByTestId('pr-section')).toBeVisible();
  // 정의서 「쓰는 곳」에 제안서가 올라갔다
  const links = await api(request, 'requirements', 'GET', `/requirements/${rq.id}/links`);
  expect(links.items.some((l: any) => l.service === 'proposal' && l.ref_id === pid)).toBeTruthy();
});

test('MI4 「제안서에 n시트 보내기」(익명) → 제안서 MI 섹션 · 연결 자료 칩 · MI 넘김 delivered', async ({ page, request }) => {
  budget(150_000);
  test.skip(!pid, '앞 단계 실패');
  await open(page, `/mi/${W.mi}/export`);
  await page.getByTestId('mi4-target').click();
  await page.getByRole('listbox', { name: '보낼 제안서' }).getByRole('option', { name: new RegExp(TITLE.replace(/[[\]]/g, '\\$&')) }).click();
  await expect(page.getByTestId('mi4-target')).toContainText(TITLE);
  await page.getByTestId('mi4-send').click();
  // 익명 꺼짐이면 실명 묻기 → 익명으로
  await clickIfShown(page, page.getByRole('button', { name: '익명으로 보내기' }), sectionUrl('mi'));
  await expect(page).toHaveURL(sectionUrl('mi'), { timeout: 60_000 });
  await until(() => lastImport(request, 'mi'), (l) => l.length > 0, 90_000, 'MI 연결');
  await until(() => sheetsOf(request, 'mi'), (s) => filled(s, ['MS', 'CB', 'CP']), 120_000, 'MI 시트');
  await page.reload();
  await expect(page.getByTestId('pr-sheet-card').first()).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('#wm-main')).toContainText('MI ·');
  await shot(page, 'J2-pr-mi-from-mi4');
  const a = await api(request, 'mi', 'GET', `/analyses/${W.mi}`);
  expect(a.links?.proposal_id ?? pid).toBe(pid);
});

test('CA5 「제안서 Why Samsung · 경쟁 비교 시트로」 → 제안서 고르기 → Why Samsung 섹션 CM · ST', async ({ page, request }) => {
  budget(150_000);
  test.skip(!pid, '앞 단계 실패');
  await open(page, `/competitor/${W.ca}/send`);
  await page.getByRole('button', { name: /제안서 Why Samsung · 경쟁 비교 시트로/ }).click();
  await clickIfShown(page, page.getByRole('button', { name: '익명으로 보내기' }), page.getByRole('list', { name: '최근 제안서' }));
  await page.getByRole('list', { name: '최근 제안서' }).getByRole('listitem').filter({ hasText: TITLE }).click();
  await expect(page).toHaveURL(sectionUrl('why'), { timeout: 60_000 });
  const sh = await until(() => sheetsOf(request, 'why'), (s) => filled(s, ['CM', 'ST']), 120_000, 'Why 시트');
  expect(sh.map((x) => x.role)).toEqual(expect.arrayContaining(['CM', 'ST']));
  const links = await lastImport(request, 'competitor');
  expect(links[0]?.ref_id).toBe(W.ca);
  await shot(page, 'J2-pr-why-from-ca5');
});

test('VP4 「제안서에 n시트 보내기」 → ?handoff=vho_ 섹션 반입 띠 · CH · VP · EF(기대 효과 추가) · VP 연결된 제안서', async ({ page, request }) => {
  budget(150_000);
  test.skip(!pid, '앞 단계 실패');
  await open(page, `/vp/${W.vp}/export`);
  const card = page.getByTestId('vp-export');
  await card.getByRole('button', { name: /연결 안 됨|·/ }).first().click();
  await page.getByRole('listbox', { name: '보낼 제안서' }).getByRole('option', { name: new RegExp(TITLE.replace(/[[\]]/g, '\\$&')) }).click();
  await expect(card).toContainText(TITLE);
  await page.getByRole('button', { name: /제안서에 \d+시트 보내기/ }).click();
  await expect(page).toHaveURL(sectionUrl('vp'), { timeout: 60_000 });
  await expect(page.getByTestId('pr-handoff-band')).toContainText('넣었어요', { timeout: 30_000 });
  const sh = await until(() => sheetsOf(request, 'vp'), (s) => filled(s, ['CH', 'VP', 'EF']), 120_000, 'VP 시트');
  expect(sh.map((x) => x.role)).toEqual(expect.arrayContaining(['CH', 'VP', 'EF']));
  const links = await lastImport(request, 'vp');
  expect(links[0]?.title).toContain('가치 제안');   // 「VP · Value Props」가 아니라 작업 제목
  const d = await api(request, 'vp', 'GET', `/vps/${W.vp}`);
  expect(d.linked_proposal?.id).toBe(pid);
  await shot(page, 'J2-pr-vp-from-vp4');
});

test('SP4 「제안서에 넣기」(제안서 바꾸기) → ?handoff=sho_ → 제품 스펙 섹션 · Spec 연결(in_sync)', async ({ page, request }) => {
  budget(150_000);
  test.skip(!pid, '앞 단계 실패');
  await open(page, `/spec/${W.sp}/export`);
  await page.getByTestId('sp-target').getByRole('button', { name: /바꾸기/ }).click();
  await page.getByRole('listbox', { name: '제안서' }).getByRole('option', { name: new RegExp(TITLE.replace(/[[\]]/g, '\\$&')) }).click();
  await expect(page.getByTestId('sp-target')).toContainText(TITLE);
  await page.getByRole('button', { name: '제안서에 넣기' }).click();
  await expect(page).toHaveURL(sectionUrl('spec'), { timeout: 60_000 });
  await expect(page.getByTestId('pr-handoff-band')).toContainText('넣었어요', { timeout: 30_000 });
  await until(() => sheetsOf(request, 'spec'), (s) => filled(s, ['SC']), 120_000, 'Spec 시트');
  const lk = await until(() => api(request, 'spec', 'GET', `/links?proposal_id=${pid}`), (x: any) => x.items.length > 0, 30_000, 'Spec 연결');
  expect(lk.items[0].sheet_id).toBe(W.sp);
  await shot(page, 'J2-pr-spec-from-sp4');
});

test('IMG4 「제안서에 넣기」(같은 프로젝트 제안서가 기본) → 시트 이미지 자리 · 이미지 정보 「사용 이력」', async ({ page, request }) => {
  budget(120_000);
  test.skip(!pid, '앞 단계 실패');
  await open(page, `/image/w/${W.imgWork}/export/${W.img}`);
  const radios = page.getByRole('radiogroup', { name: '넣을 제안서' });
  await expect(radios).toBeVisible({ timeout: 30_000 });
  // 같은 프로젝트(정의서 프로젝트)의 제안서가 기본 선택
  await expect(radios.getByRole('radio', { checked: true })).toContainText(TITLE);
  await expect(page.getByRole('radiogroup', { name: '넣을 시트' })).toBeVisible({ timeout: 30_000 });
  await page.getByRole('button', { name: '제안서에 넣기' }).click();
  await expect(page.getByText(/에 넣었어요/).first()).toBeVisible({ timeout: 30_000 });
  const imgs = await until(() => api(request, 'proposal', 'GET', `/proposals/${pid}/links`), (l: any) => l.links.some((x: any) => x.feature === 'image'), 30_000, '이미지 연결');
  expect(imgs.links.find((x: any) => x.feature === 'image').ref_id).toBe(W.img);
  const info = await api(request, 'image', 'GET', `/images/${W.img}/info`);
  expect(info.rows.find((r: any) => r.k === '사용 이력')?.v ?? '').toContain('제안서');
  await shot(page, 'J2-img4-to-proposal');
});

test('BE6 「제안서에 넣기」 → 조감도 섹션(BV · ZP) + 수량표는 공간별 제품 섹션 · BE0 쓰인 곳', async ({ page, request }) => {
  budget(150_000);
  test.skip(!pid, '앞 단계 실패');
  await open(page, `/birdseye/${W.be}/export`);
  const card = page.getByTestId('be6-proposal');
  await expect(card).toBeVisible({ timeout: 30_000 });
  if (!(await card.textContent())?.includes(TITLE)) {
    await card.getByRole('button', { name: '바꾸기' }).click();
    await page.getByRole('dialog', { name: '보낼 제안서' }).getByRole('button', { name: new RegExp(TITLE.replace(/[[\]]/g, '\\$&')) }).click();
  }
  await expect(card).toContainText(TITLE);
  await page.getByTestId('be6-send').click();
  await until(() => lastImport(request, 'birdseye'), (l) => l.length > 0, 90_000, '조감도 연결');
  const bv = await until(() => sheetsOf(request, 'birdseye'), (s) => filled(s, ['BV', 'ZP']), 120_000, '조감도 시트');
  expect(bv.map((x) => x.role)).toEqual(expect.arrayContaining(['BV', 'ZP']));
  expect(bv.some((x) => x.role === 'SM'), '수량표는 조감도 섹션에 두지 않는다').toBeFalsy();
  await until(() => sheetsOf(request, 'spaceProducts'), (s) => filled(s, ['SM']), 120_000, '공간별 제품 · 수량표');
  const links = await lastImport(request, 'birdseye');
  expect(links.map((l: any) => l.section_key)).toEqual(expect.arrayContaining(['birdseye', 'spaceProducts']));
  // BE0 쓰인 곳
  const list = await api(request, 'birdseye', 'GET', '/birdseyes?limit=20');
  const row = list.items.find((x: any) => x.id === W.be);
  expect((row.usages ?? []).some((u: any) => u.service === 'proposal' && u.ref === pid)).toBeTruthy();
  await open(page, '/birdseye');
  await expect(page.locator('#wm-main')).toContainText(`[IT] 용산 로비 조감도 ${T}`);
  await shot(page, 'J2-be0-usage');
});

test('SC5 「제안서에 넣기」(표준 → 솔루션 섹션 SXS) → SC0 「제안서에 사용 중」', async ({ page, request }) => {
  budget(150_000);
  test.skip(!pid, '앞 단계 실패');
  await open(page, `/scenario/${W.sc}/send`);
  await expect(page.getByTestId('sc5-plan')).toBeVisible({ timeout: 30_000 });
  if (!(await page.getByTestId('sc5-target').textContent())?.includes(TITLE)) {
    await page.getByTestId('sc5-target').click();
    await page.getByRole('listbox').getByRole('option', { name: new RegExp(TITLE.replace(/[[\]]/g, '\\$&')) }).click();
  }
  await expect(page.getByTestId('sc5-target')).toContainText(TITLE);
  await page.getByTestId('sc5-send').click();
  await expect(page.getByTestId('sc5-done')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId('sc5-done').getByRole('link', { name: '열기' })).toHaveAttribute('href', sectionUrl('solution'));
  const sx = await until(() => sheetsOf(request, 'solution'), (s) => filled(s, ['SXS']), 120_000, '솔루션 시트');
  expect(sx.some((x) => x.role === 'SXS')).toBeTruthy();
  const sc = await until(() => api(request, 'scenario', 'GET', `/scenarios/${W.sc}`), (x: any) => x.in_proposal, 30_000, '시나리오 사용 등록');
  expect(sc.usages.some((u: any) => u.service === 'proposal' && u.ref === pid)).toBeTruthy();
  await open(page, '/scenario/legacy');   // /scenario 는 새 흐름 목록 — 이전 시나리오 목록은 legacy
  await expect(page.locator('#wm-main')).toContainText(`[IT] 로비 방문객 동선 ${T}`);
  await shot(page, 'J2-sc0-usage');
});

/** HTML5 끌기 — 사이드바 작업 항목을 드롭 영역으로(크로미움은 마우스로 끌기를 낸다) */
async function dragTo(page: Page, src: ReturnType<Page['locator']>, dst: ReturnType<Page['locator']>) {
  const a = (await src.boundingBox())!;
  const b = (await dst.boundingBox())!;
  await page.mouse.move(a.x + 20, a.y + a.height / 2);
  await page.mouse.down();
  await page.mouse.move(a.x + 30, a.y + a.height / 2 + 4, { steps: 2 });
  await page.mouse.move(b.x + 60, b.y + b.height / 2, { steps: 12 });
  await page.waitForTimeout(150);
  await page.mouse.up();
}

test('제안서 안 끌어 놓기 — 사이드바 MI 작업 → Why Samsung 드롭 영역 → 추출 확인(DnD_MIExtract) → 이대로 반영', async ({ page, request }) => {
  budget(150_000);
  test.skip(!pid, '앞 단계 실패');
  const mi = await api(request, 'mi', 'GET', `/analyses/${W.mi}`);
  await open(page, `/proposal/${pid}/sections/why`);
  await expect(page.getByTestId('pr-section')).toBeVisible({ timeout: 30_000 });
  const group = page.locator('[data-group="mi"]');
  if (!(await group.locator('.sh-items').isVisible().catch(() => false))) await group.getByRole('button', { name: /펼치기/ }).click();
  const item = group.locator('.sh-item', { hasText: mi.title }).first();
  await expect(item).toBeVisible({ timeout: 20_000 });
  const zone = page.getByLabel('끌어 놓는 영역');
  await zone.scrollIntoViewIfNeeded();
  await dragTo(page, item, zone);
  await expect(page).toHaveURL(new RegExp(`/proposal/${pid}/sections/why/imports/imp_`), { timeout: 30_000 });
  await expect(page.getByTestId('pr-extract')).toBeVisible();
  await expect(page.getByTestId('pr-extract-row').first()).toBeVisible({ timeout: 60_000 });
  await shot(page, 'J2-pr-dnd-mi-extract');
  await page.getByTestId('pr-extract-apply').click();
  await until(() => lastImport(request, 'mi'), (l) => l.some((x: any) => x.section_key === 'why'), 90_000, 'MI → Why 연결');
});

test('딸깍(섹션에서) → 진행 · 완료 → PR6 생성 → PR7 PPTX 내려받기', async ({ page, request }) => {
  budget(420_000);
  test.skip(!pid, '앞 단계 실패');
  await open(page, `/proposal/${pid}/sections/spec?oneclick=1`);
  const pop = page.getByRole('dialog', { name: '딸깍 — 나머지 자동 완성' });
  await expect(pop).toBeVisible({ timeout: 30_000 });
  await pop.getByRole('button', { name: /딸깍, 완성하기/ }).click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${pid}/one-click/job_`), { timeout: 30_000 });
  const job = page.url().match(/job_[0-9A-Z]+/)![0];
  const done = await waitJob(request, job, 300_000);
  expect(done.status, JSON.stringify(done.error ?? {})).toBe('succeeded');
  await expect(page.getByTestId('oc-file')).toBeVisible({ timeout: 60_000 });
  await shot(page, 'J2-oneclick-done');

  // PR6 → 생성 → PR7
  await open(page, `/proposal/${pid}/design`);
  await expect(page.getByTestId('pr6')).toBeVisible();
  await page.getByTestId('pr6-generate').click();
  await clickIfShown(page, page.getByRole('dialog').getByRole('button', { name: '추론으로 채우고 만들기' }), new RegExp(`/proposal/${pid}/result`));
  await expect(page).toHaveURL(new RegExp(`/proposal/${pid}/result`), { timeout: 30_000 });
  await expect(page.getByTestId('pr7-file')).toBeVisible({ timeout: 240_000 });
  const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 60_000 }), page.getByTestId('pr7-download').click()]);
  const name = await downloadName(request, dl);
  expect(name).toMatch(/\.pptx$/);
  await shot(page, 'J2-pr7-result');
});

test('쓰는 곳 · 사용 표시 → 제안서를 지우면 조감도 · 시나리오 · 이미지 · 정의서 · VP · Spec 표시를 거둔다', async ({ page, request }) => {
  budget(90_000);
  test.skip(!pid, '앞 단계 실패');
  // 정의서 RQ6 「쓰는 곳 · 제안서」 → 이 제안서
  await open(page, `/requirements/${rq.id}`);
  await page.locator('.rq-usechip', { hasText: '제안서' }).click();
  await expect(page).toHaveURL(new RegExp(`/proposal/${pid}`), { timeout: 30_000 });
  expect((await api(request, 'spec', 'GET', `/links?proposal_id=${pid}`)).items.length).toBeGreaterThan(0);
  await request.delete(`/api/proposal/v1/proposals/${pid}`);
  // VP0 「연결된 제안서」 · Spec 연결(값 불일치 알림 대상)도 거둔다
  const vp = await api(request, 'vp', 'GET', `/vps/${W.vp}`);
  expect(vp.linked_proposal?.id ?? null).not.toBe(pid);
  expect((await api(request, 'spec', 'GET', `/links?proposal_id=${pid}`)).items).toEqual([]);
  const be = await api(request, 'birdseye', 'GET', '/birdseyes?limit=20');
  expect((be.items.find((x: any) => x.id === W.be)?.usages ?? []).some((u: any) => u.ref === pid)).toBeFalsy();
  const sc = await api(request, 'scenario', 'GET', `/scenarios/${W.sc}`);
  expect((sc.usages ?? []).some((u: any) => u.ref === pid)).toBeFalsy();
  const info = await api(request, 'image', 'GET', `/images/${W.img}/info`);
  expect(info.rows.find((r: any) => r.k === '사용 이력')?.v ?? '').not.toContain('제안서 1건');
  const links = await api(request, 'requirements', 'GET', `/requirements/${rq.id}/links`);
  expect(links.items.some((l: any) => l.service === 'proposal' && l.ref_id === pid)).toBeFalsy();
  pid = '';
});
