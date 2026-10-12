/**
 * Spec 시트 새 흐름(2026-10-12 보드 webapp1 v63 SP0 · SP1 · SP2 · SP2_Pick · SP_View · SP2_Edit · SPBody) — 실제 스택(KB 실데이터 · export · storyboard 허브).
 * Storyboard(rq → dss, API · web/e2e/shell/flowkit DSS: Smart Signage QM55C 에 KB ref) → 목록 → 「새 Spec 시트 만들기」 → 목록 위 팝업에서 Storyboard 고르기 →
 * 상세 한 장(SP2 · DSS 제품으로 표) → 형식 · 항목 바꾸기 → [확인 필요] 칸에 원문 값 → 제품 고르기(ProdPicker)에서 하나 빼기 → 저장 → 저장됨(SP_View · XLSX 내려받기)
 * → 하나 고치기 → 「고친 곳 1」 → 되돌리기 → 고치기 + 저장 · v2(SP2_Edit). 허브 stages.sp · XLSX 도 확인한다.
 * 보드 SPBody 고정 칸(띠 48 · 표 칸 190 · 160 · 항목 칸 minmax(116, 1fr) · 머리 40 · 줄 44 · 노란 칸 32 · 뺀 제품 줄 40)을 숫자로 재고 __screens__/<보드>.png 로 남긴다.
 * 실행: make e2e-feature SERVICE=spec (또는 cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=spec WM_E2E_DEV=1 WM_E2E_PORT=5206 npx playwright test e2e/spec/sp-flow.spec.ts --workers=1)
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { makeStoryboard, shotTo, tag } from '../shell/flowkit';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '__screens__');
const shot = async (page: Page, name: string) => { await page.mouse.move(10, 890); await expect(page.locator('.wm-toast')).toHaveCount(0, { timeout: 10_000 }); await shotTo(page, DIR, name); };
const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
const w = async (l: Locator) => Math.round((await l.boundingBox())!.width);
const h = async (l: Locator) => Math.round((await l.boundingBox())!.height);
const P = '[확인 필요]';
const NAMES = ['The Wall IAB 146"', 'Smart Signage QM55C', '삼성 키오스크', 'Flip Pro WA75D', 'Smart Signage QB55C', '옥외형 사이니지 OHC55'];

test('Spec 시트 상세 한 장 — 목록 · 팝업 · 새로(SP2) · 형식 · 항목 · 노란 칸 · 제품 고르기 · 저장 · 저장됨(XLSX) · 고친 곳 · 되돌리기 · v2', async ({ page, request }) => {
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `용산 AI Ready 오피스 ${tag()}`;
  const sb = await makeStoryboard(request, { dss: true, name });
  const dssRef = (await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.dss.ref as string;

  // SP0 목록 → 「새 Spec 시트 만들기」 → SP1 목록 위 팝업(보드 Gate)
  await page.goto('/spec');
  await expect(page.getByRole('heading', { name: 'Spec 시트 생성', exact: true })).toBeVisible();
  await page.getByRole('link', { name: '새 Spec 시트 만들기' }).first().click();
  await expect(page).toHaveURL(/\/spec\/new$/);
  const gate = page.getByRole('dialog', { name: /새 Spec 시트 만들기/ });
  await expect(gate).toBeVisible();
  await expect(gate.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  const gateRow = gate.getByRole('radio', { name: new RegExp(name) });
  await gateRow.click();
  await expect(gateRow).toHaveAttribute('aria-checked', 'true');
  await expect(gate.getByText('고르면 바로 Spec 시트 화면으로 넘어가요')).toBeVisible();
  await gate.getByRole('button', { name: '이 Storyboard로 시작' }).click();

  // SP2 — 새로 만들기: 상세 한 장(ContentDetail · SPBody) · DSS 제품 6개로 표를 채움 · 값은 KB 원문에서만
  await expect(page).toHaveURL(/\/spec\/flow\/sfl_[0-9A-Za-z]+$/, { timeout: 30_000 });
  const fid = page.url().split('/').pop()!;
  const code = (await (await request.get(`/api/spec/v1/spec-flows/${fid}`)).json()).code as string;
  const headEl = page.locator('.cd-head');
  await expect(headEl.locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(headEl.locator('.cd-meta')).toHaveText(`새로 만드는 중 · 쓰는 대로 작성 중으로 남아요 · 저장하면 ${sb.id}에 연결돼요`);
  await expect(page.locator('.wm-sbbar__note')).toHaveText('저장하면 이 Storyboard에 연결돼요 · 사전 작업에서 골랐어요');
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새로 만들기');
  await expect(headEl.getByRole('button', { name: '저장' })).toBeVisible();
  await expect(headEl.getByText('XLSX 내려받기')).toHaveCount(0);
  await expect(page.locator('.wm-stepper')).toHaveCount(0);                       // 스텝바 · 단계 없음
  const rows = page.getByTestId('spd-row');
  await expect(rows).toHaveCount(6);
  await expect(page.locator('.spd-name')).toHaveText(NAMES);
  const strip = page.getByTestId('spd-strip');
  await expect(strip.getByRole('radiogroup', { name: '형식' }).getByRole('radio', { name: '비교표' })).toHaveAttribute('aria-checked', 'true');
  await expect(strip.getByRole('radiogroup', { name: '표기' }).getByRole('radio', { name: '한국어 · mm' })).toHaveAttribute('aria-checked', 'true');
  await expect(strip.locator('.spd-itemsb')).toHaveText('6개 고름');
  await expect(strip.locator('.spd-src')).toHaveText('값 공식 카탈로그');
  await expect(strip.getByTestId('spd-warn')).toHaveText(/^The Wall IAB 146" · 모델 코드 확인 필요 외 \d+$/);
  await expect(strip.getByRole('button', { name: '제품 고르기 · 6/6' })).toBeVisible();
  const table = page.getByTestId('spd-table');
  await expect(table.getByRole('columnheader')).toHaveText(['제품', '공간 · 수량', '화면 크기 · 해상도', '밝기 · 명암비', '입출력 단자', '소비전력', '크기 · 무게', '설치 방식']);
  const qm = page.locator('[data-row="Smart Signage QM55C"]');
  await expect(qm.locator('.spd-space')).toHaveText('로비 · 2대');
  await expect(qm.getByRole('cell').nth(1)).toHaveText('55" · 3840×2160');            // 카탈로그 값(읽기 전용)
  const wall = page.locator('[data-row="The Wall IAB 146\\""]');
  await expect(wall.locator('.spd-space')).toHaveText('로비 · 1식');
  await expect(wall.locator('.spd-name')).toHaveClass(/spd-name--warn/);
  await expect(wall.locator('input.cd-in--warn')).toHaveCount(6);                    // 카탈로그에 없는 제품 — 칸 6개 모두 노란 칸
  await expect(page.locator('[data-row="Smart Signage QB55C"] .spd-space')).toHaveText('회의실 · 실당 1대');
  await expect(page.locator('[data-row="Flip Pro WA75D"] .spd-space')).toHaveText(`회의실 · ${P}`);
  await expect(page.locator('.spd-foot')).toHaveText('값은 공식 카탈로그에서 채워요 · 카탈로그에 없는 값은 [확인 필요]로 남기고, 노란 칸에 원문 값을 바로 적어요');
  await expect(page.getByTestId('spd-outs')).toHaveCount(0);

  // 보드 SPBody(1440 × 900): 본문 열 1180 · 본문 1100(좌우 40) · 띠 48 · 표 칸 190 · 160 · 항목 칸 (1098 − 350) / 6 = 124.67(≥ 116) · 머리 40 · 줄 44 · 노란 칸 32
  expect(await w(page.locator('.wm-flow'))).toBe(1180);
  const sb0 = await box(strip);
  expect(sb0).toMatchObject({ x: 300, w: 1100, h: 48 });
  expect(sb0.y).toBe(196);                                                             // 보드 View: 상단바 64 + SB 바 52 + 패딩 20 + 머리 46 + 사이 14
  const tb = await box(table);
  expect(tb).toMatchObject({ x: 300, y: 256, w: 1100 });                               // 띠 + 12
  const hd = table.getByRole('columnheader');
  expect(await box(hd.nth(0))).toMatchObject({ x: 301, w: 190, h: 40 });
  expect(await box(hd.nth(1))).toMatchObject({ x: 491, w: 160, h: 40 });
  expect(await w(hd.nth(2))).toBe(125);
  expect(await h(qm.locator('.spd-name'))).toBe(44);
  expect(await h(wall.locator('input').first())).toBe(32);
  expect(await w(strip.locator('.spd-seg').first())).toBeGreaterThan(130);
  expect(await h(strip.locator('.spd-seg').first())).toBe(32);
  expect(await h(strip.locator('.spd-pick'))).toBe(36);
  const foot = await box(page.locator('.spd-foot'));
  expect(foot.y + foot.h).toBeLessThanOrEqual(900 - 22);                               // 표가 남은 높이를 채우고 각주는 바닥(패딩 22) 위
  expect(tb.y + tb.h).toBe(foot.y - 12);
  await shot(page, 'SP2');

  // 형식(제품별 1장) · 항목(보증 넣기) — 누르는 즉시 저장(서버 값)
  await strip.getByRole('radio', { name: '제품별 1장' }).click();
  await expect(strip.getByRole('radio', { name: '제품별 1장' })).toHaveAttribute('aria-checked', 'true');
  await expect(page.locator('.spd-foot')).toContainText('제품별 1장은 XLSX에서 제품마다 시트 한 장으로 나눠요');
  await strip.locator('.spd-itemsb').click();
  const list = page.getByRole('listbox', { name: '항목' });
  await expect(list.getByRole('option')).toHaveText(['화면 크기 · 해상도', '밝기 · 명암비', '입출력 단자', '소비전력', '크기 · 무게', '설치 방식', '운영 시간', '보증']);
  await expect(list.locator('[aria-selected="true"]')).toHaveCount(6);
  await list.getByRole('option', { name: '보증' }).click();
  await expect(list.getByRole('option', { name: '보증' })).toHaveAttribute('aria-selected', 'true');
  await page.keyboard.press('Escape');
  await expect(list).toHaveCount(0);
  await expect(strip.locator('.spd-itemsb')).toHaveText('7개 고름');
  await expect(hd).toHaveCount(9);
  await expect(hd.last()).toHaveText('보증');
  await expect(qm.getByRole('cell').last().locator('input.cd-in--warn')).toHaveCount(1);   // 보증은 KB 에 원천이 없어 노란 칸
  // 7칸: (1098 − 350) / 7 = 106.9 < 116 → 116 고정 · 표 안에서 가로 스크롤
  expect(await w(hd.nth(2))).toBe(116);
  expect(await table.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true);

  // [확인 필요] 칸에 원문 값(떠날 때 저장) — The Wall 화면 크기 · 해상도
  const wallSize = wall.getByRole('textbox', { name: 'The Wall IAB 146" 화면 크기 · 해상도' });
  await expect(wallSize).toHaveAttribute('placeholder', P);
  await wallSize.fill('146" · 4K');
  await wallSize.press('Enter');
  await expect(wallSize).toHaveClass(/spd-in--man/);
  await expect.poll(async () => (await (await request.get(`/api/spec/v1/spec-flows/${fid}`)).json()).rows[0].manual).toEqual({ size_resolution: '146" · 4K' });

  // 제품 고르기(보드 SP2_Pick · ProdPicker 760×640) — 옥외형 사이니지 OHC55 빼기
  await strip.getByRole('button', { name: /^제품 고르기/ }).click();
  const pick = page.getByRole('dialog', { name: '스펙 시트에 넣을 제품 고르기' });
  await expect(pick).toBeVisible();
  expect(await box(pick)).toMatchObject({ w: 760, h: 640 });
  await expect(pick.getByText(`${dssRef} 제품을 모두 가져왔어요. 시트에서 뺄 것은 끄고, DSS 밖 제품도 카탈로그에서 더할 수 있어요.`)).toBeVisible();
  await expect(pick.locator('.wm-pick__group')).toHaveText([`${dssRef} · 제품`, `${dssRef} · 솔루션`]);
  await expect(pick.locator('.wm-pick__row--on')).toHaveCount(6);
  const pickRow = (n: string) => pick.locator('.wm-pick__row').filter({ has: page.locator('.wm-pick__name', { hasText: new RegExp(`^${n.replace(/[.*+?^${}()|[\]\\"]/g, '\\$&')}$`) }) });
  await expect(pickRow('Smart Signage QM55C').locator('.wm-pick__where')).toHaveText(`${dssRef} · 로비`);
  await expect(pickRow('MagicINFO')).toHaveAttribute('aria-checked', 'false');
  await expect(pickRow('MagicINFO').locator('.wm-pick__where')).toHaveText(`${dssRef} · 로비 Smart Signage QM55C`);
  await expect(pick.getByText('6개 골랐어요')).toBeVisible();
  expect(await h(pick.locator('.wm-pick__row').first())).toBe(52);
  await shot(page, 'SP2_Pick');
  await pickRow('옥외형 사이니지 OHC55').click();
  await expect(pickRow('옥외형 사이니지 OHC55')).toHaveAttribute('aria-checked', 'false');
  await expect(pick.getByText('5개 골랐어요')).toBeVisible();
  await pick.getByRole('button', { name: '완료' }).click();
  await expect(pick).toHaveCount(0);
  await expect(rows).toHaveCount(5);
  await expect(strip.getByRole('button', { name: '제품 고르기 · 5/6' })).toBeVisible();
  const outs = page.getByTestId('spd-outs');
  await expect(outs).toBeVisible();
  await expect(outs.locator('.spd-outs__k')).toHaveText('시트에서 뺀 제품');
  await expect(outs.locator('.spd-out')).toHaveText(['옥외형 사이니지 OHC55다시 넣기']);
  expect(await box(outs)).toMatchObject({ x: 300, w: 1100, h: 40 });
  // 작성 중(draft): 머리 알약 · 한 줄
  await expect(headEl.locator('.cd-ref')).toHaveText('작성 중');
  await expect(headEl.locator('.cd-meta')).toHaveText(new RegExp(`^작성 중 · 제품 5 · 확인 필요 \\d+ · 오늘 \\d\\d:\\d\\d 자동 저장 · 저장하면 ${sb.id}에 연결돼요$`));

  // 형식은 비교표로 되돌려 저장 → 그 자리에서 저장됨(SP_View) · 토스트 · XLSX 내려받기
  await strip.getByRole('radio', { name: '비교표' }).click();
  await expect(strip.getByRole('radio', { name: '비교표' })).toHaveAttribute('aria-checked', 'true');
  await headEl.getByRole('button', { name: '저장' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: `${code} v1 저장 · ${code}_v1.xlsx 만들었어요` })).toBeVisible({ timeout: 30_000 });
  await expect(page).toHaveURL(new RegExp(`/spec/flow/${fid}$`));
  await expect(headEl.locator('.cd-ref')).toHaveText(`${code} v1`);
  await expect(headEl.locator('.cd-meta')).toHaveText(/^오늘 \d\d:\d\d 저장 · 제품 5 · 항목 7 · 비교표$/);
  await expect(headEl.locator('.cd-hint')).toHaveText('눌러서 바로 고쳐요');
  await expect(headEl.getByRole('button', { name: /저장/ })).toHaveCount(0);
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(code);
  const dl = headEl.getByRole('link', { name: 'XLSX 내려받기' });
  await expect(dl).toHaveAttribute('download', `${code}_v1.xlsx`);
  expect(await h(dl)).toBe(38);
  await expect(headEl.getByRole('button', { name: 'flow.json' })).toBeVisible();
  await expect(page.locator('.cd-next')).toHaveCount(0);                                   // Spec 시트는 후속 작업 없음
  const xr = await request.get((await dl.getAttribute('href'))!);
  expect(xr.status()).toBe(200);
  expect(xr.headers()['content-type']).toContain('spreadsheetml');
  const [download] = await Promise.all([page.waitForEvent('download'), dl.click()]);
  expect(download.suggestedFilename()).toBe(`${code}_v1.xlsx`);
  await shot(page, 'SP_View');

  const flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const ssp = flow.stages.sp;
  expect(ssp).toMatchObject({ ref: code, ver: 1, from: dssRef, format: '비교표', lang: 'ko', unit: 'mm', valuesFrom: '공식 카탈로그', file: `${code}_v1.xlsx` });
  expect(ssp.columns.map((c: { key: string }) => c.key)).toEqual(['size_resolution', 'brightness_contrast', 'io_ports', 'power', 'size_weight', 'install', 'warranty']);
  expect(ssp.models.map((m: { name: string }) => m.name)).toEqual(NAMES.slice(0, 5));
  expect(ssp.models[0]).toMatchObject({ model_code: null, qty: 1, manualSpecs: ['size_resolution'] });
  expect(ssp.models[0].specs.size_resolution).toBe('146" · 4K');
  expect(ssp.models[1]).toMatchObject({ space: '로비', model_code: 'LH55QMCEBGCXKR', ref: 'kb:model:LH55QMCEBGCXKR', qty: 2 });
  expect(ssp.models[1].specs.size_resolution).toBe('55" · 3840×2160');
  expect(flow.cells.find((c: { key: string }) => c.key === 'sp')).toMatchObject({ state: 'done', ref: code, route: `/spec/flow/${fid}` });

  // 저장한 것을 하나 고치기(시트에서 뺀 OHC55 다시 넣기) → 고치는 중 · 「고친 곳 1」 · 되돌리기
  await outs.getByRole('button', { name: '옥외형 사이니지 OHC55 다시 넣기' }).click();
  await expect(rows).toHaveCount(6);
  await expect(page.getByTestId('spd-outs')).toHaveCount(0);
  await expect(headEl.locator('.cd-chg')).toHaveText('고친 곳 1');
  await expect(headEl.locator('.cd-ref')).toHaveText(`${code} v1 · 고치는 중`);
  await expect(headEl.locator('.cd-meta')).toHaveText(`${code} v1 고치는 중 · 저장하면 v2 · ${sb.id}에 반영돼요`);
  await expect(page.locator('[data-row="옥외형 사이니지 OHC55"] .spd-name')).toHaveClass(/cd-chgrow/);
  await expect(headEl.getByRole('button', { name: '저장 · v2' })).toBeVisible();
  await headEl.getByRole('button', { name: '되돌리기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: `${code} v1로 되돌렸어요` })).toBeVisible();
  await expect(headEl.locator('.cd-chg')).toHaveCount(0);
  await expect(headEl.locator('.cd-ref')).toHaveText(`${code} v1`);
  await expect(rows).toHaveCount(5);
  await expect(page.getByTestId('spd-outs')).toBeVisible();
  expect((await (await request.get(`/api/spec/v1/spec-flows/${fid}`)).json()).changes).toBe(0);

  // 다시 고치기(보드 SP2_Edit: 고친 곳 2 · 항목 + 보증 · OHC55 는 「시트에서 뺀 제품」) — 항목에서 보증을 뺐다 넣는 대신 운영 시간을 넣고 · 키오스크 칸에 원문 값
  await strip.locator('.spd-itemsb').click();
  await page.getByRole('listbox', { name: '항목' }).getByRole('option', { name: '운영 시간' }).click();
  await page.keyboard.press('Escape');
  await expect(strip.locator('.spd-itemsb')).toHaveText('7개 + 운영 시간 고름');
  await expect(strip.locator('.spd-itemsb')).toHaveClass(/spd-itemsb--chg/);
  await expect(hd.nth(8)).toHaveText('운영 시간');
  await expect(hd.nth(8)).toHaveClass(/spd-h--new/);
  const kioskPow = page.getByRole('textbox', { name: '삼성 키오스크 소비전력' });
  await kioskPow.fill('120 W');
  await kioskPow.press('Tab');
  await expect(kioskPow).toHaveClass(/cd-in--chg/);
  await expect(headEl.locator('.cd-chg')).toHaveText('고친 곳 2');
  await expect(headEl.getByRole('link', { name: 'XLSX 내려받기' })).toBeVisible();     // 고치는 중에도 저장한 판의 XLSX
  await page.getByTestId('spd-table').evaluate((el) => { el.scrollLeft = 0; });
  await shot(page, 'SP2_Edit');
  expect(await box(page.getByTestId('spd-outs'))).toMatchObject({ x: 300, w: 1100, h: 40 });

  // 고치는 중 다른 화면으로 가면 묻는다 → 계속 고치기
  await page.locator('.sh-group__link', { hasText: 'Spec 시트 생성' }).first().click();
  const leave = page.getByRole('dialog', { name: '저장하지 않은 고친 곳' });
  await expect(leave).toBeVisible();
  await expect(leave).toContainText('고친 곳 2개를 아직 저장하지 않았어요');
  await leave.getByRole('button', { name: '계속 고치기' }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/flow/${fid}$`));

  // 저장 · v2 → 저장됨 · XLSX v2 · 허브 stages.sp v2
  await headEl.getByRole('button', { name: '저장 · v2' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: `${code} v2 저장 · ${code}_v2.xlsx 만들었어요` })).toBeVisible({ timeout: 30_000 });
  await expect(headEl.locator('.cd-ref')).toHaveText(`${code} v2`);
  await expect(headEl.locator('.cd-chg')).toHaveCount(0);
  await expect(kioskPow).not.toHaveClass(/cd-in--chg/);
  await expect(strip.locator('.spd-itemsb')).toHaveText('8개 고름');
  await expect(headEl.getByRole('link', { name: 'XLSX 내려받기' })).toHaveAttribute('download', `${code}_v2.xlsx`);
  const ssp2 = (await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.sp;
  expect(ssp2).toMatchObject({ ver: 2, file: `${code}_v2.xlsx` });
  expect(ssp2.models[2]).toMatchObject({ name: '삼성 키오스크', manualSpecs: ['power'] });
  expect(ssp2.models[2].specs.power).toBe('120 W');

  // 목록 · 팝업: 저장된 카드 · Gate 는 「있음 · 열어 고치기」 → 같은 상세
  await page.goto('/spec');
  const card = page.locator('.fl-card').filter({ hasText: `${code} v2` });
  await expect(card).toBeVisible();
  await expect(card.locator('.fl-cardtitle')).toHaveAttribute('href', `/spec/flow/${fid}`);
  await page.goto('/spec/new');
  const again = page.getByRole('radio', { name: new RegExp(name) });
  await expect(again).toContainText(`${code} v2 있음`);
  await again.click();
  await page.getByRole('button', { name: `${code} 열어 고치기` }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/flow/${fid}$`));
  await expect(page.locator('.cd-head .cd-ref')).toHaveText(`${code} v2`);
});

test('Spec 시트 — 후속 「만들기」(?sb=&auto=1) 바로 상세 · 1920 폭 · 저장 막힘 · 옛 주소(?step=) · 이전 흐름 경로', async ({ page, request }) => {
  test.setTimeout(180_000);
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });
  // CF-07: 팝업을 건너뛰고 바로 만든다
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(`/spec/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/spec\/flow\/sfl_[0-9A-Za-z]+$/, { timeout: 30_000 });
  const fid = page.url().split('/').pop()!;
  await expect(page.getByTestId('spd-row')).toHaveCount(6);
  // 1920 폭: 본문 열은 1180 그대로(셸이 가운데) · 칸 190 · 160 · 높이는 화면을 채운다(표 안에서만 스크롤)
  expect(await w(page.locator('.wm-flow'))).toBe(1180);
  expect(await w(page.getByTestId('spd-strip'))).toBe(1100);
  expect(await w(page.getByTestId('spd-table').getByRole('columnheader').nth(0))).toBe(190);
  expect(await w(page.getByTestId('spd-table').getByRole('columnheader').nth(1))).toBe(160);
  const foot = await box(page.locator('.spd-foot'));
  expect(foot.y + foot.h).toBeLessThanOrEqual(1080 - 22);
  expect(foot.y + foot.h).toBeGreaterThan(1080 - 22 - 20);
  expect(await page.evaluate(() => document.scrollingElement!.scrollHeight <= window.innerHeight + 1)).toBe(true);
  await shot(page, 'SP2-1920');

  // 항목을 모두 빼면 저장이 막힌다(이유는 버튼 title · 누르면 토스트)
  await page.setViewportSize({ width: 1440, height: 900 });
  const strip = page.getByTestId('spd-strip');
  await strip.locator('.spd-itemsb').click();
  const list = page.getByRole('listbox', { name: '항목' });
  for (const t of ['화면 크기 · 해상도', '밝기 · 명암비', '입출력 단자', '소비전력', '크기 · 무게', '설치 방식']) await list.getByRole('option', { name: t }).click();
  await page.keyboard.press('Escape');
  await expect(strip.locator('.spd-itemsb')).toHaveText('0개 고름');
  const save = page.locator('.cd-head').getByRole('button', { name: '저장' });
  await expect(save).toHaveAttribute('aria-disabled', 'true');
  await expect(save).toHaveAttribute('title', '항목을 하나 이상 골라 주세요');
  await expect(page.getByTestId('spd-table').getByText('항목을 하나 이상 골라 주세요')).toBeVisible();
  await save.click({ force: true });                                                    // aria-disabled — 눌러도 저장하지 않고 이유를 알린다
  await expect(page.locator('.wm-toast').filter({ hasText: '항목을 하나 이상 골라 주세요' })).toBeVisible();
  expect((await (await request.get(`/api/spec/v1/spec-flows/${fid}`)).json()).ver).toBeNull();
  // 저장 전 되돌리기 API 는 409 NOT_SAVED
  const rv = await request.post(`/api/spec/v1/spec-flows/${fid}:revert`);
  expect(rv.status()).toBe(409);
  expect((await rv.json()).error).toMatchObject({ code: 'NOT_SAVED', message: '아직 저장하지 않아 되돌릴 판이 없어요' });

  // 옛 주소(단계 쿼리)로 와도 상세 한 장
  await page.goto(`/spec/flow/${fid}?step=done`);
  await expect(page.getByTestId('spd-strip')).toBeVisible();
  await expect(page.locator('.cd-head .cd-ref')).toHaveText('작성 중');

  // 이전 흐름: 목록 · 새로 만들기는 /spec/legacy · 넘겨받은 모델(`/spec/new?models=`)은 이전 입력 화면으로
  await page.goto('/spec/legacy');
  await expect(page.getByRole('heading', { name: 'Spec 시트 작업' })).toBeVisible();
  await expect(page.locator('a.sp-start', { hasText: '조건으로 모델 찾기' })).toHaveAttribute('href', '/spec/legacy/new/find');
  await page.goto('/spec/new/find');
  await expect(page).toHaveURL(/\/spec\/legacy\/new\/find$/);
  await page.goto('/spec/new?models=LH55QMCEBGCXKR');
  await expect(page).toHaveURL(/\/spec\/(legacy\/new\?models=|sp_[A-Z0-9]+\/products)/, { timeout: 20_000 });
});
