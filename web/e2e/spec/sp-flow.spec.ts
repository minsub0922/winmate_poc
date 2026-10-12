/**
 * Spec 시트 새 흐름(보드 webapp1 v62 — SP0 · 최종본 View content=sp(SP_View · SP_Draft) + 단계 팝업 SP1 · SP2 · SP2_Edit · JsonPopup) —
 * 실제 스택(KB 실데이터 · export · storyboard 허브).
 * Storyboard(rq → dss, API · web/e2e/shell/flowkit DSS: Smart Signage QM55C 에 KB ref) → 목록 → 새로 만들기(빈 최종본 + ① Gate 팝업) → ② 시트 작성 팝업
 * (제품 체크 · 모델 바꾸기 · 모델 고르기 · 수량 · 항목 · 형식 · 표기) → 시트 만들기 → 팝업이 닫히고 최종본(XLSX 내려받기 · 옵션 줄 · 비교표 · flow.json) ·
 * 허브 stages.sp → 단계 칩으로 고치기 팝업(저장 · v2 · 닫기 물음).
 * 상세에는 페이지 이동이 없다(같은 주소 · `?step=sheet`). 팝업은 1440×900 에서 (130, 50) 1180×800 — 칸 좌표는 예전 SP2 페이지에서 x −130 · y −50
 * (팝업 머리 72 − 상단바 · 스텝바 · SB 바 172 + 팝업 위 50). 보드 SP2 고정 칸(330 · 머리 40 · 줄 44 · 선택 줄 46 · 미리보기 머리 38 · 항목 칸 130 · 칸 36 · 버튼 48)과
 * 보드 View(옵션 줄 44 · 비교표 190 · 160 · 머리 40 · 줄 44)를 숫자로 재고 __screens__/<보드>-new.png 로 남긴다.
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

test('Spec 시트 새 흐름 — 목록 · Gate 팝업 · 시트 작성 팝업(모델 · 수량 · 항목 · 형식 · 표기) · 저장 → 최종본 · 허브 stages.sp · 고치기 v2', async ({ page, request }) => {
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

  // SP1 — 빈 최종본(새로 만들기 · ② 자리표시) 위 ① Storyboard 팝업(보드 SP1 = Gate content=sp)
  await expect(page).toHaveURL(/\/spec\/new$/);
  const gateDlg = page.getByRole('dialog', { name: '새 Spec 시트 · Storyboard' });
  await expect(gateDlg).toBeVisible();
  expect(await box(gateDlg)).toEqual({ x: 130, y: 50, w: 1180, h: 800 });
  await expect(gateDlg.locator('.fl-shead__mode')).toHaveText('새로 만들기');
  await expect(gateDlg.locator('.fl-shead__pos')).toHaveText('단계 1/2');
  await expect(gateDlg.locator('.fl-shead__note')).toHaveText('Storyboard를 고르면 Spec 시트가 그 Storyboard에 연결돼요 · 고르기 전에 닫으면 목록으로');
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'new');
  await expect(page.locator('.fl-detail .fl-dver')).toHaveText('새로 만들기');
  await expect(page.locator('.fl-slot')).toHaveCount(1);
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새로 만들기');
  await expect(page.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  await expect(gateDlg.locator('.wm-flow__back')).toHaveCount(0);                  // 팝업 안에서는 「목록」 링크 없음(×로 닫는다)
  await expect(page.getByText('최소 DSS까지 완료된 Storyboard이 있어야 시작할 수 있어요.', { exact: false })).toBeVisible();
  const gateRow = page.getByRole('radio', { name: new RegExp(name) });
  await gateRow.click();
  await expect(gateRow).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByText(`${name}에 Spec 시트가 연결돼요`)).toBeVisible();
  await shot(page, 'SP1-new');
  await page.getByRole('button', { name: '이 Storyboard로 시작' }).click();

  // SP2 — ② 시트 작성 팝업(같은 최종본 위 · 주소는 ?step=sheet): DSS 제품 6개(공간 · 수량 원문) · KB 모델 맞춤 · 카탈로그 값
  await expect(page).toHaveURL(/\/spec\/flow\/sfl_[0-9A-Za-z]+\?step=sheet$/, { timeout: 30_000 });
  const fid = page.url().split('/').pop()!.split('?')[0];
  await expect(page.getByRole('heading', { name: 'DSS 제품으로 스펙 시트를 만들어요' })).toBeVisible();
  await expect(page.getByText(`${dssRef}에서 고른 제품을 그대로 가져왔어요. 값은 공식 카탈로그에서 채워요.`)).toBeVisible();
  const stepDlg = page.locator('.fl-stepdlg');
  expect(await box(stepDlg)).toEqual({ x: 130, y: 50, w: 1180, h: 800 });
  await expect(stepDlg.locator('.fl-shead__row b')).toHaveText(name);
  await expect(stepDlg.locator('.fl-shead__sb')).toContainText(name);
  await expect(stepDlg.locator('.fl-shead__note')).toHaveText('Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨');
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText('새로 만들기');
  await expect(stepDlg.locator('.fl-shead__pos')).toHaveText('단계 2/2');
  await expect(stepDlg.locator('.wm-sbbar')).toHaveCount(0);
  await expect(stepDlg.locator('.wm-flow__back')).toHaveCount(0);                  // 팝업 안에서는 「Storyboard」 뒤로 링크 없음
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새로 만들기');
  // 팝업 뒤 최종본: 아직 저장 전(새로 만들기) · ② 자리표시(다음 단계 · 「이어서」는 닫은 뒤에만)
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'new');
  await expect(page.locator('.fl-detail .fl-dhead__meta')).toHaveText('아직 저장 전 · 단계 2/2 진행 중 · 팝업을 닫아도 작성 중으로 남아요');
  await expect(page.locator('[data-slot="2"]')).toContainText('DSS 제품의 스펙 비교표 · XLSX — 이 단계를 마치면 여기에 채워져요');
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
  // 보드 SP2(팝업 1180 × 800 · 본문 728) 칸: 본문 1180 · 제품 330 | 오른쪽 756(1100 − 330 − 14) · 머리 40 · 줄 44 · 선택 줄 46 · 미리보기 머리 38 · 항목 칸 130 · 칸 36 ·
  // 제품 칸 3개 폭((754 − 130) / 3 = 208, 넘치면 가로 스크롤) · 시트 만들기 48(y 782 = 50 + 800 − 20 − 48).
  // 세로 위치는 앱과 같은 Noto Sans KR(줄 높이 normal: h1 34 · 설명 19 → 머리 57)로 잰 값 — 보드 jpg 는 머리 54(그리드 y 208 · 미리보기 y 400).
  expect(await w(page.locator('.fl-sbody .wm-flow'))).toBe(1180);
  expect(await box(page.getByTestId('sf-products'))).toEqual({ x: 170, y: 211, w: 330, h: 559 });
  expect(await box(page.getByTestId('sf-options'))).toEqual({ x: 514, y: 211, w: 756, h: 181 });   // 46 + 79(칩 두 줄 78 + 선) + 46 + 패딩 8 + 선 2
  expect(await box(pv)).toEqual({ x: 514, y: 404, w: 756, h: 366 });
  expect(await box(page.locator('.sf-lhead'))).toMatchObject({ w: 328, h: 40 });
  expect(await box(rows.first())).toMatchObject({ w: 328, h: 44 });
  expect(await h(page.locator('.sf-opt').first())).toBe(46);
  expect(await h(page.locator('.sf-chip').first())).toBe(30);
  expect(await w(page.locator('.sf-opt__k').first())).toBe(64);
  expect(await box(pv.locator('.sf-preview__h'))).toMatchObject({ w: 754, h: 38 });
  expect(await box(pv.locator('.sf-cell--head').first())).toMatchObject({ w: 130, h: 36 });
  expect(await w(pv.locator('.sf-cell--head').nth(1))).toBe(208);
  expect(await h(pv.locator('.sf-cell--label').nth(1))).toBe(36);
  expect(await box(page.getByRole('button', { name: '시트 만들기' }))).toMatchObject({ y: 782, h: 48 });
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

  // 시트 만들기 → 팝업이 닫히고 같은 주소의 최종본(보드 SP_View · 완료 화면 없음) · XLSX · 허브 flow.json stages.sp
  await page.getByRole('button', { name: '시트 만들기' }).click();
  await expect(stepDlg).toHaveCount(0, { timeout: 30_000 });
  await expect(page).toHaveURL(new RegExp(`/spec/flow/${fid}$`));
  await expect(page.getByRole('heading', { name: 'Spec 시트를 만들었어요' })).toHaveCount(0);
  const code = doc.code as string;
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'saved');
  await expect(view.locator('h1')).toHaveText(name);
  await expect(view.locator('.fl-dver')).toHaveText(`${code} v1`);
  await expect(view.locator('.fl-dhead__meta')).toHaveText(/^오늘 \d\d:\d\d 저장 · 제품 5 · 항목 6 · 비교표$/);
  await expect(view.locator('.fl-dnav__label')).toHaveText('단계별 고치기');
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(code);
  await expect(page.locator('.wm-sbbar__chip').first()).toContainText(name);
  // 머리: XLSX 내려받기(단계 칩 앞) · flow.json
  const dl = view.getByRole('link', { name: 'XLSX 내려받기' });
  await expect(dl).toHaveAttribute('download', `${code}_v1.xlsx`, { timeout: 15_000 });
  const headBtns = await view.locator('.fl-dhead > .fl-dbtn, .fl-dhead > .fl-dnav').evaluateAll((els) => els.map((e) => (e.classList.contains('fl-dnav') ? '단계' : e.textContent?.trim())));
  expect(headBtns).toEqual(['XLSX 내려받기', '단계', '{ }flow.json']);              // 보드 View: XLSX 내려받기 → 단계 칩 → flow.json
  // 본문: 옵션 줄(형식 · 표기 · 값 · 파일 + 경고 칩) → 비교표(제품 · 공간 · 수량 · 항목 6) → 아래 안내
  const opt = view.getByTestId('spv-options');
  await expect(opt.locator('.spv-opt')).toHaveText(['형식비교표', '표기한국어 · mm', '값공식 카탈로그', `파일${code}_v1.xlsx`]);
  await expect(opt.locator('.spv-warn').first()).toHaveText('The Wall IAB 146" · 카탈로그에 없음');
  const tbl = view.getByTestId('spv-table');
  await expect(tbl.getByRole('columnheader')).toHaveText(['제품', '공간 · 수량', '화면 크기 · 해상도', '밝기 · 명암비', '입출력 단자', '소비전력', '크기 · 무게', '운영 시간']);
  await expect(tbl.getByRole('rowheader')).toHaveText(['The Wall IAB 146"', 'Smart Signage QM55C', 'Flip Pro WA75D', 'Smart Signage QB55C', '옥외형 사이니지 OHC55']);
  const vqm = tbl.locator('[data-vrow="Smart Signage QM55C"]');
  await expect(vqm.getByRole('cell')).toHaveText(['로비 · 3대', '55" · 3840×2160', /.+/, /.+/, /.+/, /.+/, /.+/]);     // 고친 수량(3) · 카탈로그 값
  await expect(tbl.getByText('24/7').first()).toBeVisible();
  const vwall = tbl.locator('[data-vrow="The Wall IAB 146\\""]');
  await expect(vwall.getByRole('cell').first()).toHaveText('로비 · 1식');
  await expect(vwall.locator('.spv-c--pend')).toHaveCount(6);                                   // 카탈로그에 없는 제품 → 값은 [확인 필요](주황)
  await expect(vwall.locator('.spv-c--pend').first()).toHaveText(P);
  await expect(vwall.getByRole('rowheader')).toHaveClass(/spv-c--pw/);
  await expect(tbl.locator('[data-vrow="Flip Pro WA75D"]').getByRole('cell').first()).toHaveText(`회의실 · ${P}`);
  await expect(tbl.locator('[data-vrow="Smart Signage QB55C"]').getByRole('cell').first()).toHaveText('회의실 · 실당 1대');
  await expect(view.locator('.fl-vfoot')).toHaveText('값은 공식 카탈로그에서 채워요 · 카탈로그에 없는 값은 [확인 필요]로 남겨요');
  await expect(view.locator('.fl-dfollow')).toHaveCount(0);                                    // 후속 작업 없음
  // 보드 View(content=sp): 본문 1100 · 옵션 줄 44 · 비교표 190 | 160 | 항목(1098 − 350) / 6 · 머리 40 · 줄 44 · 아래 안내까지 화면 안
  expect(await box(opt)).toMatchObject({ x: 300, w: 1100, h: 44 });
  expect(await w(tbl)).toBe(1100);
  expect(await box(tbl.getByRole('columnheader').nth(0))).toMatchObject({ w: 190, h: 40 });
  expect(await w(tbl.getByRole('columnheader').nth(1))).toBe(160);
  expect(await w(tbl.getByRole('columnheader').nth(2))).toBe(125);
  expect(await h(tbl.getByRole('rowheader').first())).toBe(44);
  expect(await h(dl)).toBe(38);
  const foot = await box(view.locator('.fl-vfoot'));
  expect(foot.y + foot.h).toBeLessThanOrEqual(900 - 24);
  await shot(page, 'SP_View-new');

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
  await expect(page.locator('.wm-sbbar__stage').first()).toContainText('DSS');
  // XLSX 내려받기(files 서비스 · 게이트웨이)
  const xr = await request.get((await dl.getAttribute('href'))!);
  expect(xr.status()).toBe(200);
  expect(xr.headers()['content-type']).toContain('spreadsheetml');

  // flow.json(보드 JsonPopup 900 × 780 · stages.sp 강조)
  await view.getByRole('button', { name: 'flow.json' }).click();
  const jd = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(jd).toBeVisible();
  expect(await box(jd)).toMatchObject({ w: 900, h: 780 });
  await expect(jd.getByText('"sp": {').first()).toBeVisible();
  await expect(jd.locator('.wm-jsonline--add').first()).toBeVisible();
  await shot(page, 'SP_ViewJson-new');
  await jd.getByRole('button', { name: '닫기' }).last().click();
  await expect(jd).toHaveCount(0);

  // 단계 칩 「시트 작성」 → 고치기 팝업(보드 SP2_Edit: SP-nn v1 고치기 · 저장 · v2 · 뒤로 링크 없음) — 고치지 않고 닫으면 묻지 않는다
  await view.getByRole('button', { name: /^시트 작성 · / }).click();
  await expect(page).toHaveURL(/step=sheet/);
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText(`${code} v1 고치기`);
  await expect(stepDlg.locator('.fl-shead__note')).toHaveText(`저장하면 ${code} v2 · ${sb.id}에 반영돼요`);
  await expect(stepDlg.locator('.fl-shead__pos')).toHaveText('단계 2/2');
  await expect(stepDlg.getByRole('button', { name: '저장 · v2' })).toBeVisible();
  await expect(stepDlg.getByRole('button', { name: '시트 만들기' })).toHaveCount(0);
  await expect(stepDlg.locator('.wm-flow__back')).toHaveCount(0);
  await expect(page.locator('.sf-lhead__n')).toHaveText('5 / 6 선택');
  expect(await box(page.getByRole('button', { name: '저장 · v2' }))).toMatchObject({ y: 782, h: 48 });
  await shot(page, 'SP2_Edit-new');
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(stepDlg).toHaveCount(0);
  await expect(page.getByRole('dialog', { name: '고친 내용을 저장할까요?' })).toHaveCount(0);
  // 고친 뒤 닫으면 저장할지 묻는다(한 번) → 「저장 · v2」 → 최종본 v2 · XLSX v2(설치 방식 항목 다시 넣기)
  await view.getByRole('button', { name: /^시트 작성 · / }).click();
  await expect(stepDlg).toBeVisible();
  await stepDlg.getByRole('group', { name: '항목' }).getByRole('button', { name: '설치 방식' }).click();
  await expect(stepDlg.getByRole('group', { name: '항목' }).getByRole('button', { name: '설치 방식' })).toHaveAttribute('aria-pressed', 'true');
  await expect.poll(async () => (await (await request.get(`/api/spec/v1/spec-flows/${fid}`)).json()).items.length).toBe(7);
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  const ask = page.getByRole('dialog', { name: '고친 내용을 저장할까요?' });
  await expect(ask).toBeVisible();
  await expect(ask.getByRole('button')).toHaveText(['계속 고치기', '저장하지 않고 닫기', '저장 · v2']);
  await shot(page, 'SP2_EditAsk-new');
  await ask.getByRole('button', { name: '저장 · v2' }).click();
  await expect(ask).toHaveCount(0);
  await expect(stepDlg).toHaveCount(0, { timeout: 30_000 });
  await expect(view.locator('.fl-dver')).toHaveText(`${code} v2`);
  await expect(view.locator('.fl-dhead__meta')).toContainText('제품 5 · 항목 7 · 비교표');
  await expect(view.getByRole('link', { name: 'XLSX 내려받기' })).toHaveAttribute('download', `${code}_v2.xlsx`);
  await expect(tbl.getByRole('columnheader')).toHaveCount(9);
  expect((await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.sp).toMatchObject({ ver: 2, file: `${code}_v2.xlsx` });

  // 목록에 저장된 줄(코드 v2 · Storyboard 칩) · Gate 는 「있음 · 수정」 → 최종본 위 고치기 팝업으로
  await page.goto('/spec');
  const listRow = page.locator('.fl-card').filter({ hasText: `${code} v2` });
  await expect(listRow).toBeVisible();
  await expect(listRow.getByRole('button', { name: sb.name })).toBeVisible();
  await expect(listRow.locator('.fl-cardtitle')).toHaveAttribute('href', `/spec/flow/${fid}`);
  await page.goto('/spec/new');
  const again = page.getByRole('radio', { name: new RegExp(name) });
  await expect(again).toContainText(`${code} v2 있음`);
  await again.click();
  await expect(page.getByText(new RegExp(`이 Storyboard에는 Spec 시트 ${code} v2[이가] 이미 있어요`))).toBeVisible();
  await page.getByRole('button', { name: `${code} 수정하기` }).click();
  await expect(page).toHaveURL(new RegExp(`/spec/flow/${fid}\\?step=sheet$`));
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(code);
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText(`${code} v2 고치기`);
  // 저장된 것을 그냥 열면 최종본만(팝업 없음)
  await page.goto(`/spec/flow/${fid}`);
  await expect(view).toHaveAttribute('data-status', 'saved');
  await expect(stepDlg).toHaveCount(0);
});

test('Spec 시트 새 흐름 — Storyboard · DSS 의 「만들기」(?sb=&auto=1)는 Gate 를 건너뛰고 ② 팝업 · 1920 폭 · 작성 중 닫기 · 이전 흐름 경로', async ({ page, request }) => {
  test.setTimeout(180_000);
  const name = `용산 AI Ready 오피스 ${tag()}`;
  const sb = await makeStoryboard(request, { dss: true, name });
  // CF-07: Gate 를 건너뛰고 바로 만든다 → 빈 최종본 위 ② 시트 작성 팝업
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(`/spec/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/spec\/flow\/sfl_[0-9A-Za-z]+\?step=sheet$/, { timeout: 30_000 });
  await expect(page.getByRole('heading', { name: 'DSS 제품으로 스펙 시트를 만들어요' })).toBeVisible();
  await expect(page.locator('.fl-shead__sb')).toContainText(name);
  await expect(page.getByTestId('sf-row')).toHaveCount(6);
  // 1920 × 1080: 팝업은 가운데 1180 × 800 그대로 · 제품 330 | 오른쪽 756 · 시트 만들기는 팝업 바닥에서 20 위
  expect(await box(page.locator('.fl-stepdlg'))).toEqual({ x: 370, y: 140, w: 1180, h: 800 });
  expect(await w(page.locator('.fl-sbody .wm-flow'))).toBe(1180);
  expect(await box(page.getByTestId('sf-products'))).toMatchObject({ w: 330, h: 559 });
  expect(await w(page.getByTestId('sf-preview'))).toBe(756);
  const btn = await box(page.getByRole('button', { name: '시트 만들기' }));
  expect(btn.y + btn.h).toBe(140 + 800 - 20);
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

  // 저장 전에 닫으면 작성 중 최종본(보드 SP_Draft: 작성 중 1/2 · ② 자리표시에 「이어서 · 시트 작성」) → 다시 열면 같은 팝업
  await page.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(page.locator('.fl-stepdlg')).toHaveCount(0);
  await expect(page).not.toHaveURL(/step=/);
  await expect(page.getByRole('dialog', { name: '고친 내용을 저장할까요?' })).toHaveCount(0);   // 저장 전 초안은 묻지 않는다
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'draft');
  await expect(view.locator('.fl-dver')).toHaveText('작성 중 1/2');
  await expect(view.locator('.fl-dhead__meta')).toHaveText(new RegExp(`^작성 중 · 2단계 중 1단계 마침 · 오늘 \\d\\d:\\d\\d · 저장하면 ${sb.id}에 연결돼요$`));
  await expect(view.locator('.fl-dnav__label')).toHaveText('단계 1/2');
  await expect(view.getByRole('link', { name: 'XLSX 내려받기' })).toHaveCount(0);
  await expect(view.getByRole('button', { name: 'flow.json' })).toHaveCount(0);
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(name);
  const slot = page.locator('[data-slot="2"]');
  await expect(slot).toContainText('시트 작성 단계');
  expect(await box(slot)).toMatchObject({ x: 300, w: 1100 });
  const sbox = await box(slot);
  expect(sbox.y + sbox.h).toBe(900 - 24);                                                      // 큰 자리표시가 본문 아래까지
  await shot(page, 'SP_Draft-new');
  await slot.getByRole('button', { name: '이어서 · 시트 작성' }).click();
  await expect(page).toHaveURL(/step=sheet/);
  await expect(page.locator('.fl-stepdlg .fl-shead__mode')).toHaveText('새로 만들기');
  await expect(page.getByRole('group', { name: '항목' }).locator('[aria-pressed="true"]')).toHaveCount(1);
  // 작성 중을 주소로(목록 · 작업 내역) 열면 ② 팝업이 열린 채로
  const fid = page.url().split('/').pop()!.split('?')[0];
  await page.goto(`/spec/flow/${fid}`);
  await expect(page).toHaveURL(new RegExp(`/spec/flow/${fid}\\?step=sheet$`));
  await expect(page.locator('.fl-stepdlg')).toBeVisible();
  // ① 고르기 팝업을 고르기 전에 닫으면 목록
  await page.goto('/spec/new');
  await page.getByRole('dialog', { name: '새 Spec 시트 · Storyboard' }).getByRole('button', { name: '팝업 닫기' }).click();
  await expect(page).toHaveURL(/\/spec$/);
  expect((await request.delete(`/api/spec/v1/spec-flows/${fid}`)).status()).toBe(204);     // 정리

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
