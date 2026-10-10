/**
 * Spec 시트 새 흐름(2026-10-08 보드 webapp1 SP0 · SP1 · SP2 · SP_Done · JsonPopup) — 실제 스택(KB 실데이터 · export · storyboard 허브).
 * Storyboard(rq → dss, API · web/e2e/shell/flowkit DSS: Smart Signage QM55C 에 KB ref) → 목록 → Gate → SP2(제품 체크 · 모델 바꾸기 · 모델 고르기 ·
 * 수량 · 항목 · 형식 · 표기) → 시트 만들기 → 완료(XLSX · 요약본 · 접힌 JSON · 전체 JSON) · 허브 stages.sp.
 * 보드 SP2 고정 칸(330 · 머리 40 · 줄 44 · 선택 줄 46 · 미리보기 머리 38 · 항목 칸 130 · 칸 36 · 버튼 48)을 숫자로 재고 __screens__/<보드>-new.png 로 남긴다.
 * 실행: cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=spec WM_E2E_DEV=1 WM_E2E_PORT=5206 npx playwright test e2e/spec/sp-flow.spec.ts --workers=1
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { makeStoryboard, shotTo, tag } from '../shell/flowkit';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '__screens__');
const shot = async (page: Page, name: string) => { await page.mouse.move(10, 890); await shotTo(page, DIR, name); };
const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
const w = async (l: Locator) => Math.round((await l.boundingBox())!.width);
const h = async (l: Locator) => Math.round((await l.boundingBox())!.height);
const P = '[확인 필요]';

test('Spec 시트 새 흐름 — 목록 · Gate · 시트 작성(모델 · 수량 · 항목 · 형식 · 표기) · 저장 · 완료 · 허브 stages.sp', async ({ page, request }) => {
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `용산 AI Ready 오피스 ${tag()}`;
  const sb = await makeStoryboard(request, { dss: true, name });
  const dssRef = (await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.dss.ref as string;

  // SP0 — 목록(보드 List content=sp)
  await page.goto('/spec');
  await expect(page.getByRole('heading', { name: 'Spec 시트 생성', exact: true })).toBeVisible();
  await expect(page.getByText('DSS에서 고른 제품의 스펙 시트를 만들어요.')).toBeVisible();
  await expect(page.getByText('사전 작업 · 최소 DSS까지 된 Storyboard')).toBeVisible();
  await expect(page.getByText('후속 작업 · 없음')).toBeVisible();
  expect(await w(page.locator('.fl-list'))).toBe(1180);
  await shot(page, 'SP0-new');
  await page.getByRole('link', { name: '새 Spec 시트' }).first().click();

  // SP1 — 사전 작업 고르기(보드 Gate content=sp)
  await expect(page).toHaveURL(/\/spec\/new$/);
  await expect(page.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  await expect(page.getByText('최소 DSS까지 완료된 Storyboard이 있어야 시작할 수 있어요.', { exact: false })).toBeVisible();
  const gateRow = page.getByRole('radio', { name: new RegExp(name) });
  await gateRow.click();
  await expect(gateRow).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByText(`${name}에 Spec 시트가 연결돼요`)).toBeVisible();
  await shot(page, 'SP1-new');
  await page.getByRole('button', { name: '이 Storyboard로 시작' }).click();

  // SP2 — 시트 작성: DSS 제품 6개(공간 · 수량 원문) · KB 모델 맞춤 · 카탈로그 값
  await expect(page).toHaveURL(/\/spec\/flow\/sfl_[0-9A-Za-z]+$/, { timeout: 30_000 });
  const fid = page.url().split('/').pop()!;
  await expect(page.getByRole('heading', { name: 'DSS 제품으로 스펙 시트를 만들어요' })).toBeVisible();
  await expect(page.getByText(`${dssRef}에서 고른 제품을 그대로 가져왔어요. 값은 공식 카탈로그에서 채워요.`)).toBeVisible();
  await expect(page.locator('.wm-sbbar__chip')).toContainText(name);
  await expect(page.locator('.wm-sbbar__note')).toHaveText('Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨');
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새 Spec 시트');
  const rows = page.getByTestId('sf-row');
  await expect(rows).toHaveCount(6);
  await expect(rows.locator('.sf-row__t')).toHaveText(['The Wall IAB 146"', 'Smart Signage QM55C', '삼성 키오스크', 'Flip Pro WA75D', 'Smart Signage QB55C', '옥외형 사이니지 OHC55']);
  await expect(page.locator('.sf-lhead__n')).toHaveText('6 / 6 선택');
  const qmRow = page.locator('[data-row="Smart Signage QM55C"]');
  await expect(qmRow.locator('.sf-row__sp')).toHaveText('로비');
  await expect(qmRow.locator('.sf-model')).toHaveText('QM55C');
  const wallRow = page.locator('[data-row="The Wall IAB 146\\""]');
  await expect(wallRow.locator('.sf-row__sp')).toHaveText('로비 · 카탈로그에 없음');
  await expect(wallRow.locator('.sf-model')).toHaveText('모델 고르기');
  // 형식 · 항목 · 표기 칩(보드 기본: 비교표 · 앞 6개 항목 · 한국어 · mm)
  const items = page.getByRole('group', { name: '항목' });
  await expect(items.getByRole('button')).toHaveText(['화면 크기 · 해상도', '밝기 · 명암비', '입출력 단자', '소비전력', '크기 · 무게', '설치 방식', '운영 시간', '보증']);
  await expect(items.locator('[aria-pressed="true"]')).toHaveCount(6);
  await expect(page.getByRole('group', { name: '형식' }).getByRole('button', { name: '비교표' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('group', { name: '표기' }).getByRole('button', { name: '한국어 · mm' })).toHaveAttribute('aria-pressed', 'true');
  // 미리보기 · 비교표: 값은 KB 원문에서만, 카탈로그에 없는 제품은 [확인 필요]
  const pv = page.getByTestId('sf-preview');
  await expect(pv.locator('.sf-preview__h')).toHaveText('미리보기 · 비교표');
  await expect(pv.locator('.sf-cell--head')).toHaveText(['항목', 'The Wall IAB 146"', 'Smart Signage QM55C', '삼성 키오스크', 'Flip Pro WA75D', 'Smart Signage QB55C', '옥외형 사이니지 OHC55']);
  await expect(pv.locator('.sf-cell--label:not(.sf-cell--head)')).toHaveText(['화면 크기 · 해상도', '밝기 · 명암비', '입출력 단자', '소비전력', '크기 · 무게', '설치 방식']);
  await expect(pv.getByText('55" · 3840×2160').first()).toBeVisible();
  await expect(pv.locator('.sf-cell--pend').first()).toHaveText(P);
  await expect(page.locator('.wm-flow__summary')).toHaveText(/^확인 필요 값 \d+ · 경고 \d+$/);
  // 보드 SP2(1440 × 900) 칸: 본문 1180 · 제품 330 | 오른쪽 756(1100 − 330 − 14) · 머리 40 · 줄 44 · 선택 줄 46 · 미리보기 머리 38 · 항목 칸 130 · 칸 36 ·
  // 제품 칸 3개 폭((754 − 130) / 3 = 208, 넘치면 가로 스크롤) · 시트 만들기 48(y 832 = 900 − 20 − 48).
  // 세로 위치는 앱과 같은 Noto Sans KR(줄 높이 normal: h1 34 · 설명 19 → 머리 57)로 잰 값 — 보드 jpg 는 머리 54(그리드 y 258 · 선택 180 · 미리보기 y 450).
  expect(await w(page.locator('.wm-flow'))).toBe(1180);
  expect(await box(page.getByTestId('sf-products'))).toEqual({ x: 300, y: 261, w: 330, h: 559 });
  expect(await box(page.getByTestId('sf-options'))).toEqual({ x: 644, y: 261, w: 756, h: 181 });   // 46 + 79(칩 두 줄 78 + 선) + 46 + 패딩 8 + 선 2
  expect(await box(pv)).toEqual({ x: 644, y: 454, w: 756, h: 366 });
  expect(await box(page.locator('.sf-lhead'))).toMatchObject({ w: 328, h: 40 });
  expect(await box(rows.first())).toMatchObject({ w: 328, h: 44 });
  expect(await h(page.locator('.sf-opt').first())).toBe(46);
  expect(await h(page.locator('.sf-chip').first())).toBe(30);
  expect(await w(page.locator('.sf-opt__k').first())).toBe(64);
  expect(await box(pv.locator('.sf-preview__h'))).toMatchObject({ w: 754, h: 38 });
  expect(await box(pv.locator('.sf-cell--head').first())).toMatchObject({ w: 130, h: 36 });
  expect(await w(pv.locator('.sf-cell--head').nth(1))).toBe(208);
  expect(await h(pv.locator('.sf-cell--label').nth(1))).toBe(36);
  expect(await box(page.getByRole('button', { name: '시트 만들기' }))).toMatchObject({ y: 832, h: 48 });
  await shot(page, 'SP2-new');

  // 모델 바꾸기(같은 제품군) — QM55C → QM65C: 불일치 경고 · 값 다시 채움 → 수량 · QM55C 로 되돌리기
  await qmRow.getByRole('button', { name: 'Smart Signage QM55C 모델 바꾸기' }).click();
  const dlg = page.getByRole('dialog', { name: 'Smart Signage QM55C 모델 고르기' });
  await expect(dlg).toBeVisible();
  expect(await box(dlg)).toMatchObject({ w: 760, h: 640 });
  await expect(dlg.locator('.sf-dlg__group')).toHaveText(/^같은 제품군 · /);
  await expect(dlg.getByRole('radio', { name: /QM55C/ })).toHaveAttribute('aria-checked', 'true');
  await expect(dlg.locator('.sf-dlg__note')).toHaveText('DSS · 로비 2대');
  await expect(dlg.getByRole('textbox', { name: 'Smart Signage QM55C 수량' })).toHaveValue('2');
  expect(await h(dlg.locator('.sf-dlg__opt').first())).toBe(52);
  expect(await h(dlg.locator('.sf-dlg__search'))).toBe(38);
  await dlg.getByRole('radio', { name: /^QM65C/ }).click();
  await expect(dlg.getByRole('radio', { name: /^QM65C/ })).toHaveAttribute('aria-checked', 'true', { timeout: 15_000 });
  await expect(dlg.locator('.sf-dlg__warns')).toContainText('모델 불일치');
  await expect(dlg.locator('.sf-dlg__warns')).toContainText('DSS 제품명(QM55C)과 고른 모델(QM65C)이 달라요');
  await expect(qmRow.locator('.sf-model')).toHaveText('QM65C');
  await expect(qmRow.locator('.sf-row__sp')).toHaveText('로비 · 모델 불일치');
  await expect(pv.getByText('65" · 3840×2160').first()).toBeVisible();
  await shot(page, 'SP2_Model-new');
  await dlg.getByRole('textbox', { name: 'Smart Signage QM55C 수량' }).fill('3');
  await dlg.getByRole('textbox', { name: 'Smart Signage QM55C 수량' }).press('Enter');
  await dlg.getByRole('radio', { name: /^QM55C/ }).click();
  await expect(dlg.getByRole('radio', { name: /^QM55C/ })).toHaveAttribute('aria-checked', 'true', { timeout: 15_000 });
  await expect(dlg.locator('.sf-dlg__warns')).toHaveCount(0);
  await dlg.getByRole('button', { name: '완료' }).click();
  await expect(dlg).toHaveCount(0);
  await expect(qmRow.locator('.sf-model')).toHaveText('QM55C');
  await expect(qmRow.locator('.sf-row__sp')).toHaveText('로비');

  // 모델 고르기(카탈로그에 없던 제품) — 옥외형 사이니지 OHC55: 이름으로 못 찾음 → 「OH55」 검색 → OH55A(실외용) · 불일치는 경고로 남는다
  const ohRow = page.locator('[data-row="옥외형 사이니지 OHC55"]');
  await expect(ohRow.locator('.sf-row__sp')).toHaveText('주차장 · 카탈로그에 없음');
  await ohRow.getByRole('button', { name: '옥외형 사이니지 OHC55 모델 고르기' }).click();
  const dlg2 = page.getByRole('dialog', { name: '옥외형 사이니지 OHC55 모델 고르기' });
  await expect(dlg2.locator('.sf-dlg__warns')).toContainText('공식 카탈로그에서 모델을 찾지 못했어요');
  await expect(dlg2.getByText('찾은 모델이 없어요 · 아래에서 모델명이나 모델코드로 찾아보세요')).toBeVisible({ timeout: 15_000 });
  await expect(dlg2.locator('.sf-dlg__note')).toHaveText(`DSS · 주차장 ${P}`);
  await expect(dlg2.getByRole('textbox', { name: '옥외형 사이니지 OHC55 수량' })).toHaveValue('');
  await dlg2.getByRole('textbox', { name: '카탈로그에서 다른 모델 찾기' }).fill('OH55');
  await dlg2.getByRole('radio', { name: /^OH55A/ }).click({ timeout: 15_000 });
  await expect(dlg2.getByRole('radio', { name: /^OH55A/ })).toHaveAttribute('aria-checked', 'true', { timeout: 15_000 });
  await expect(dlg2.locator('.sf-dlg__warns')).toContainText('DSS 제품명(OHC55)과 고른 모델(OH55A)이 달라요');
  await dlg2.getByRole('button', { name: '완료' }).click();
  await expect(ohRow.locator('.sf-model')).toHaveText('OH55A');
  await expect(ohRow.locator('.sf-row__sp')).toHaveText('주차장 · 모델 불일치');

  // 제품 빼기 · 항목(운영 시간 넣기 · 설치 방식 빼기) · 표기(영문 · inch) · 형식(제품별 1장) → 되돌리기
  await page.getByRole('checkbox', { name: '삼성 키오스크' }).click();
  await expect(page.getByRole('checkbox', { name: '삼성 키오스크' })).toHaveAttribute('aria-checked', 'false');
  await expect(page.locator('.sf-lhead__n')).toHaveText('5 / 6 선택');
  await expect(pv.locator('.sf-cell--head')).toHaveCount(6);
  await items.getByRole('button', { name: '운영 시간' }).click();
  await items.getByRole('button', { name: '설치 방식' }).click();
  await expect(pv.locator('.sf-cell--label:not(.sf-cell--head)')).toHaveText(['화면 크기 · 해상도', '밝기 · 명암비', '입출력 단자', '소비전력', '크기 · 무게', '운영 시간']);
  await expect(pv.getByText('24/7').first()).toBeVisible();
  await page.getByRole('group', { name: '표기' }).getByRole('button', { name: '영문 · inch' }).click();
  await expect(pv.locator('.sf-cell--head').first()).toHaveText('Item');
  await expect(pv.locator('.sf-cell--label:not(.sf-cell--head)').first()).toHaveText('Screen Size · Resolution');
  await expect(items.getByRole('button').first()).toHaveText('화면 크기 · 해상도');      // 칩은 화면 말 그대로
  await expect(pv.getByText('[To be confirmed]').first()).toBeVisible();
  await page.getByRole('group', { name: '형식' }).getByRole('button', { name: '제품별 1장' }).click();
  await expect(pv.locator('.sf-preview__h')).toHaveText('미리보기 · 제품별 1장');
  await expect(pv.locator('.sf-one')).toHaveCount(5);
  await expect(pv.locator('.sf-one').nth(1).locator('.sf-one__head')).toContainText('Smart Signage QM55C');
  await expect(pv.locator('.sf-one').nth(1).locator('.sf-one__head')).toContainText('QM55C · LH55QMCEBGCXKR · 로비 · Qty 3');
  await shot(page, 'SP2_PerProduct-new');
  await page.getByRole('group', { name: '형식' }).getByRole('button', { name: '비교표' }).click();
  await page.getByRole('group', { name: '표기' }).getByRole('button', { name: '한국어 · mm' }).click();
  await expect(pv.locator('.sf-cell--head').first()).toHaveText('항목');
  await expect(pv.locator('.sf-preview__h')).toHaveText('미리보기 · 비교표');
  const doc = await (await request.get(`/api/spec/v1/spec-flows/${fid}`)).json();
  expect(doc).toMatchObject({ format: 'compare', notation: 'ko_mm', items: ['size_resolution', 'brightness_contrast', 'io_ports', 'power', 'size_weight', 'operation_hours'] });
  expect(doc.counts).toMatchObject({ models: 5, total: 6, columns: 6 });

  // 시트 만들기 → SP_Done(보드 Done content=sp) · XLSX · 허브 flow.json stages.sp
  await page.getByRole('button', { name: '시트 만들기' }).click();
  await expect(page.getByRole('heading', { name: 'Spec 시트를 만들었어요' })).toBeVisible({ timeout: 30_000 });
  const code = doc.code as string;
  await expect(page.locator('.wm-done__head .wm-flow__desc')).toHaveText('제품 5개 · 비교표 · XLSX로 내보낼 수 있어요');
  const dl = page.getByRole('link', { name: 'XLSX로 내보낼 수 있어요' });
  await expect(dl).toHaveAttribute('download', `${code}_v1.xlsx`);
  await expect(page.locator('.wm-done__md pre')).toHaveText(new RegExp(`^## Spec · ${code} v1\\n- 제품 5 · 항목 6 · 비교표 · 한국어 · mm\\n- 확인 필요 값 \\d+ · 경고 \\d+$`));
  await expect(page.getByText(/"stages\.sp": \{/)).toBeVisible();
  await expect(page.locator('.wm-done__json pre')).toContainText('"format": "비교표"');
  await expect(page.locator('.wm-done__json pre')).toContainText(`"file": "${code}_v1.xlsx"`);
  await expect(page.locator('.wm-done__stage--cur')).toContainText('Spec');
  await expect(page.locator('.wm-done__stage--cur')).toContainText(code);
  await expect(page.locator('.wm-sbbar__note')).toHaveText('요약본이 방금 갱신됐어요');
  await expect(page.locator('.sf-nofollow')).toContainText('이 콘텐츠는 후속 작업이 없어요. Storyboard에서 다른 콘텐츠를 이어서 만들 수 있어요.');
  await expect(page.locator('.sf-nofollow').getByRole('link', { name: 'Storyboard로' })).toHaveAttribute('href', `/storyboard/flow/${sb.id}`);
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(code);
  // 보드 Done: 본문 좌우 80 → 카드 1020 · 요약 · JSON 상자 248 + 선
  expect(await w(page.locator('.wm-done__card'))).toBe(1020);
  expect(await h(page.locator('.wm-done__md'))).toBe(250);
  await shot(page, 'SP_Done-new');

  const flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const ssp = flow.stages.sp;
  expect(ssp).toMatchObject({ ref: code, ver: 1, from: dssRef, format: '비교표', lang: 'ko', unit: 'mm', valuesFrom: '공식 카탈로그', file: `${code}_v1.xlsx` });
  expect(ssp.columns.map((c: { key: string }) => c.key)).toEqual(['size_resolution', 'brightness_contrast', 'io_ports', 'power', 'size_weight', 'operation_hours']);
  expect(ssp.models.map((m: { name: string }) => m.name)).toEqual(['The Wall IAB 146"', 'Smart Signage QM55C', 'Flip Pro WA75D', 'Smart Signage QB55C', '옥외형 사이니지 OHC55']);
  const qm = ssp.models[1];
  expect(qm).toMatchObject({ space: '로비', model_code: 'LH55QMCEBGCXKR', ref: 'kb:model:LH55QMCEBGCXKR', qty: 3, by: 'manual' });
  expect(qm.specs.size_resolution).toBe('55" · 3840×2160');
  expect(ssp.models[0]).toMatchObject({ model_code: null, ref: null, qty: 1 });
  expect(Object.values(ssp.models[0].specs)).toEqual(Array(6).fill(P));
  expect(ssp.models[2].qty).toBeNull();                                    // DSS 수량 없음 → 지어내지 않는다
  const wk = ssp.warnings.map((x: { model: string; kind: string }) => `${x.model}:${x.kind}`);
  expect(wk).toEqual(expect.arrayContaining(['The Wall IAB 146":not_in_catalog', 'Flip Pro WA75D:not_in_catalog', 'OH55A:mismatch']));
  expect(wk.some((x: string) => x.startsWith('QM55C:'))).toBe(false);
  expect(ssp.counts).toMatchObject({ models: 5, columns: 6, warnings: ssp.warnings.length });
  const cell = flow.cells.find((c: { key: string }) => c.key === 'sp');
  expect(cell).toMatchObject({ state: 'done', ref: code, route: `/spec/flow/${fid}` });
  expect(flow.cards.sp.facts[0]).toEqual(['제품', '5']);
  // XLSX 내려받기(files 서비스 · 게이트웨이)
  const xr = await request.get((await dl.getAttribute('href'))!);
  expect(xr.status()).toBe(200);
  expect(xr.headers()['content-type']).toContain('spreadsheetml');

  await page.getByRole('button', { name: '전체 JSON 보기' }).click();
  const jd = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(jd).toBeVisible();
  expect(await box(jd)).toMatchObject({ w: 900, h: 780 });
  await expect(jd.getByText('"sp": {').first()).toBeVisible();
  await expect(jd.locator('.wm-jsonline--add').first()).toBeVisible();
  await shot(page, 'SP_DoneJson-new');
  await jd.getByRole('button', { name: '닫기' }).last().click();

  // 다시 고치기 → 같은 시트(상단바 제목 = 코드) · 목록에 저장된 줄(코드 v1 · Storyboard 칩) · Gate 는 「있음 · 수정」
  await page.getByRole('button', { name: '다시 고치기' }).click();
  await expect(page.getByRole('heading', { name: 'DSS 제품으로 스펙 시트를 만들어요' })).toBeVisible();
  await expect(page.locator('.sf-lhead__n')).toHaveText('5 / 6 선택');
  await page.goto('/spec');
  const listRow = page.getByRole('row').filter({ hasText: `${code} v1` });
  await expect(listRow).toBeVisible();
  await expect(listRow.getByRole('button', { name: sb.name })).toBeVisible();
  await expect(listRow.getByRole('link', { name: '열기' })).toHaveAttribute('href', `/spec/flow/${fid}`);
  await page.goto('/spec/new');
  const again = page.getByRole('radio', { name: new RegExp(name) });
  await expect(again).toContainText(`${code} v1 있음`);
  await again.click();
  await expect(page.getByText(`이 Storyboard에는 Spec 시트 ${code} v1이 이미 있어요`)).toBeVisible();
  await page.getByRole('button', { name: `${code} 수정하기` }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/flow/${fid}$`));
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(code);
});

test('Spec 시트 새 흐름 — DSS 완료 화면 「만들기」(?sb=&auto=1) · 1920 폭 · 이전 흐름 경로', async ({ page, request }) => {
  test.setTimeout(180_000);
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });
  // CF-07: Gate 를 건너뛰고 바로 만든다
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(`/spec/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/spec\/flow\/sfl_[0-9A-Za-z]+$/, { timeout: 30_000 });
  await expect(page.getByRole('heading', { name: 'DSS 제품으로 스펙 시트를 만들어요' })).toBeVisible();
  await expect(page.getByTestId('sf-row')).toHaveCount(6);
  // 1920 폭: 본문 열은 1180 그대로(셸이 가운데) · 제품 330 · 높이는 화면을 채운다(패널 안에서만 스크롤)
  expect(await w(page.locator('.wm-flow'))).toBe(1180);
  expect(await w(page.getByTestId('sf-products'))).toBe(330);
  expect(await w(page.getByTestId('sf-preview'))).toBe(756);
  const btn = await box(page.getByRole('button', { name: '시트 만들기' }));
  expect(btn.y + btn.h).toBe(1080 - 20);
  expect(await page.evaluate(() => document.scrollingElement!.scrollHeight <= window.innerHeight + 1)).toBe(true);
  await shot(page, 'SP2-1920-new');

  // 넣을 제품이 없거나 항목이 없으면 시트 만들기를 못 한다(이유는 아래 줄)
  await page.setViewportSize({ width: 1440, height: 900 });
  const items = page.getByRole('group', { name: '항목' });
  for (const t of ['화면 크기 · 해상도', '밝기 · 명암비', '입출력 단자', '소비전력', '크기 · 무게', '설치 방식']) await items.getByRole('button', { name: t }).click();
  await expect(items.locator('[aria-pressed="true"]')).toHaveCount(0);
  await expect(page.getByRole('button', { name: '시트 만들기' })).toBeDisabled();
  await expect(page.locator('.wm-flow__summary')).toHaveText('항목을 하나 이상 골라 주세요');
  await expect(page.getByTestId('sf-preview').getByText('항목을 하나 이상 골라 주세요')).toBeVisible();
  await items.getByRole('button', { name: '보증' }).click();
  await expect(page.getByRole('button', { name: '시트 만들기' })).toBeEnabled();
  await expect(page.getByTestId('sf-preview').locator('.sf-cell--label:not(.sf-cell--head)')).toHaveText(['보증']);

  // 이전 흐름: 목록 · 새로 만들기는 /spec/legacy · 넘겨받은 모델(`/spec/new?models=`)은 이전 입력 화면으로
  await page.goto('/spec/legacy');
  await expect(page.getByRole('heading', { name: 'Spec 시트 작업' })).toBeVisible();
  await expect(page.locator('a.sp-start', { hasText: '조건으로 모델 찾기' })).toHaveAttribute('href', '/spec/legacy/new/find');
  await expect(page.locator('a.sp-start', { hasText: '모델명으로 입력' })).toHaveAttribute('href', '/spec/legacy/new');
  await page.goto('/spec/new/find');
  await expect(page).toHaveURL(/\/spec\/legacy\/new\/find$/);
  await page.goto('/spec/new?models=LH55QMCEBGCXKR');
  await expect(page).toHaveURL(/\/spec\/(legacy\/new\?models=|sp_[A-Z0-9]+\/products)/, { timeout: 20_000 });
});
