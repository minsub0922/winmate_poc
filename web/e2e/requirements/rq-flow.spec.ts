/**
 * 고객 요구사항 새 흐름(보드 webapp1 v62 — RQ0 · 최종본 View content=rq · RQ_Draft + 단계 팝업 RQ1 · RQ1_Edit) — 실제 스택(mock 모델 · mocks/ai-tools/rq.flow_extract.v1).
 * 목록 → 새 요구사항(빈 최종본 + ① 요구사항 입력 팝업) → 파일로 채우기 → 직접 입력 → 저장하면 팝업이 닫히고 최종본(완료 화면 없음 · Storyboard 자동 생성)
 * → 단계 칩으로 고치기 팝업(RQ1_Edit: RQ-nn v1 고치기 · 저장 · v2 · 고친 뒤 닫으면 물음) → v2.
 * 상세에는 페이지 이동이 없다(같은 화면 · `?step=input`). 팝업은 1440×900 에서 (130, 50) 1180×800 — 칸 좌표는 팝업 기준(예전 page 좌표에서 x −130 · y −50 · 팝업 머리 72).
 * AI 심층 질의(폼 개선 과정)는 2026-10-12 에 뺐다 — 버튼 · 패널 · API 가 없어야 한다.
 * 보드의 고정 칸 폭(400 · 본문 1180 · 최종본 340)을 숫자로 재고, 화면을 __screens__/<보드>-new.png 로 남긴다.
 * 실행: make e2e-feature SERVICE=requirements (1 worker)
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { DSS_VALUE, internalHeaders, tag } from '../shell/flowkit';
import { shot } from './helpers';

const K_MEMO = `K 리츠 미팅 회의록 — 성수 플래그십 리테일 리뉴얼
참석: 자산관리팀장, 마케팅 리드
- 자산관리팀장: 1층 파사드 미디어로 집객, 테넌트별 콘텐츠 운영, 시설 원격 관리
- 마케팅 리드: 시즌 캠페인 빠른 교체, 방문객 데이터 활용
`;

const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { w: Math.round(b.width * 10) / 10, h: Math.round(b.height * 10) / 10, x: Math.round(b.x), y: Math.round(b.y) }; };
const w = async (l: Locator) => Math.round((await l.boundingBox())!.width);
const h = async (l: Locator) => Math.round((await l.boundingBox())!.height);

/** 팝업 안 입력 화면의 칸 폭(보드 RQ1: 본문 1180 · 왼쪽 400 | 오른쪽 684 · 끌어 놓기 1100) */
async function widths(page: Page) {
  const dlg = page.locator('.fl-stepdlg');
  return {
    flow: await w(dlg.locator('.wm-flow')),
    main: await w(dlg.locator('.rqf-main')),
    left: await w(dlg.locator('.rqf-left')),
    right: await w(dlg.locator('.rqf-right')),
    drop: await w(dlg.locator('.rqf-drop')),
  };
}

test('RQ 새 흐름 — 목록 · 빈 최종본 + 입력 팝업 · 파일 · 저장 → 최종본 · Storyboard 자동 생성 · 고치기 v2', async ({ page, request }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1440, height: 900 });

  // RQ0 — 목록(보드 List content=rq)
  await page.goto('/requirements');
  await expect(page.getByRole('heading', { name: '고객 요구사항', exact: true })).toBeVisible();
  await expect(page.getByText('가장 첫 단위예요. 저장하면 Storyboard가 자동으로 만들어져요.')).toBeVisible();
  await page.getByRole('link', { name: '새 요구사항' }).first().click();

  // RQ1 — 빈 최종본(새로 만들기 · ① 자리표시) 위 ① 요구사항 입력 팝업(사전 작업이 없어 Gate 없이 바로 폼)
  await expect(page).toHaveURL(/\/requirements\/new$/);
  const dlg = page.getByRole('dialog', { name: '새 요구사항 · 요구사항 입력' });
  await expect(dlg).toBeVisible();
  expect(await box(dlg)).toMatchObject({ x: 130, y: 50, w: 1180, h: 800 });
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'new');
  await expect(view.locator('.fl-dver')).toHaveText('새로 만들기');
  await expect(view.locator('h1')).toHaveText('새 요구사항');
  await expect(view.locator('.fl-slot')).toHaveCount(1);
  await expect(view.locator('.wm-sbbar__empty')).toHaveText('저장하면 이 요구사항으로 Storyboard가 자동으로 만들어져요');
  await expect(dlg.locator('.fl-shead__mode')).toHaveText('새로 만들기');
  await expect(dlg.locator('.fl-shead__note')).toHaveText('저장하면 이 요구사항으로 Storyboard가 자동으로 만들어져요');
  await expect(dlg.locator('.fl-shead__sb')).toHaveCount(0);
  await expect(dlg.locator('.fl-shead__pos')).toHaveText('단계 1/1');
  await expect(dlg.locator('.wm-sbbar')).toHaveCount(0);
  await expect(dlg.getByRole('heading', { name: '고객 요구사항 입력' })).toBeVisible();
  await expect(dlg.getByText('모두 선택 항목이에요')).toBeVisible();
  await expect(dlg.getByRole('link', { name: '목록' })).toHaveCount(0);
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새로 만들기');
  // 보드 RQ1(팝업): 본문 1180 · 왼쪽 400 | 오른쪽 1fr(1180 − 80 − 400 − 16 = 684) · 머리 줄 40(y 144) · 끌어 놓기 줄 1100×64(x 170 · y 198) · 입력 42 · 저장 48(y 778)
  expect(await widths(page)).toEqual({ flow: 1180, main: 1180, left: 400, right: 684, drop: 1100 });
  expect(await box(dlg.locator('.rqf-head'))).toMatchObject({ h: 40, y: 144 });
  expect(await box(dlg.locator('.rqf-drop'))).toMatchObject({ h: 64, x: 170, y: 198 });
  expect(await box(dlg.locator('.rqf-left'))).toMatchObject({ x: 170, y: 276 });
  await expect(dlg.getByRole('button', { name: /AI 심층 질의/ })).toHaveCount(0);
  expect(await h(dlg.locator('#rq-proj'))).toBe(42);
  expect(await box(dlg.getByRole('button', { name: '저장', exact: true }))).toMatchObject({ h: 48, y: 778 });
  expect(await h(dlg.locator('.rqf-role').first())).toBe(34);
  expect(await h(dlg.locator('.rqf-w').first())).toBe(28);

  // 파일 첨부 → 문서가 생기고(주소만 /requirements/flow/rqf_…?step=input · 같은 팝업) 잡이 빈 칸을 채운다(mock: 회의록 K 리츠)
  await dlg.locator('input[type=file][aria-label="파일 첨부"]').setInputFiles({ name: '회의록_K리츠.txt', mimeType: 'text/plain', buffer: Buffer.from(K_MEMO) });
  await expect(page).toHaveURL(/\/requirements\/flow\/rqf_[0-9A-Za-z]+\?step=input$/, { timeout: 15_000 });
  await expect(dlg).toBeVisible();
  await expect(dlg.locator('.rqf-chip')).toHaveText('회의록_K리츠.txt에서 읽음', { timeout: 30_000 });
  await expect(dlg.locator('#rq-proj')).toHaveValue('성수 플래그십 리테일 리뉴얼');
  await expect(dlg.locator('#rq-cust')).toHaveValue('K 리츠');
  await expect(dlg.locator('#rq-to')).toHaveValue('');
  await expect(dlg.locator('#rq-to')).toHaveAttribute('placeholder', '예) 대표이사');
  await expect(dlg.locator('#rq-k0')).toHaveValue('자산관리팀장');
  await expect(dlg.locator('#rq-k1')).toHaveValue('마케팅 리드');
  await expect(dlg.locator('.rqf-w')).toHaveText(['60%', '40%']);
  await expect(dlg.getByRole('textbox', { name: '마케팅 리드 요구 2' })).toHaveValue('방문객 데이터 활용');
  await expect(dlg.locator('[data-req]').nth(4).locator('.rqf-tag--vague')).toHaveText('범위 불명확');
  await expect(dlg.getByText('가중치 합 100%')).toBeVisible();
  // 팝업 머리 이름은 저장 전 내내 「새 요구사항」(보드 RQ1) · 뒤 최종본은 그대로 새로 만들기
  await expect(dlg.locator('.fl-shead__row b')).toHaveText('새 요구사항');
  await expect(view).toHaveAttribute('data-status', 'new');
  const flowId = new URL(page.url()).pathname.split('/').pop()!;

  // 직접 입력 — 제작자 의견(고객 문서 · Storyboard 에서 빠진다) · 자동 저장
  await dlg.locator('#rq-note').fill('설계 단계 스펙인이 목표');
  await expect.poll(async () => (await (await request.get(`/api/requirements/v1/rq-flows/${flowId}`)).json()).note, { timeout: 10_000 }).toBe('설계 단계 스펙인이 목표');
  await dlg.locator('#rq-note').blur();
  await page.mouse.move(10, 890);
  await shot(page, 'RQ1-new');

  // 최종 제안대상은 직접 적는다(AI 심층 질의 없음 — 경로도 없다)
  expect([404, 405]).toContain((await request.post(`/api/requirements/v1/rq-flows/${flowId}/deep-questions`)).status());
  await dlg.locator('#rq-to').fill('자산관리본부장');
  await expect.poll(async () => (await (await request.get(`/api/requirements/v1/rq-flows/${flowId}`)).json()).target, { timeout: 10_000 }).toBe('자산관리본부장');
  await expect(dlg.locator('#rq-to')).not.toHaveClass(/--ai/);
  await expect(dlg.locator('.rqf-aitag, .rqf-w--ai, .rqf-tag--ai')).toHaveCount(0);

  // 저장 → 팝업이 닫히고 같은 주소의 최종본(보드 RQ_View · 완료 안내 화면 없음) · Storyboard 자동 생성(안내 토스트)
  await dlg.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.locator('.fl-stepdlg')).toHaveCount(0, { timeout: 20_000 });
  await expect(page).toHaveURL(new RegExp(`/requirements/flow/${flowId}$`));
  await expect(page.getByRole('heading', { name: '요구사항을 저장했어요' })).toHaveCount(0);
  const toastLine = page.getByText(/Storyboard ‘성수 플래그십 리테일’\((SB-[0-9A-Za-z]+)\)[이가] 자동으로 만들어졌어요/);
  await expect(toastLine).toBeVisible();
  const sbId = /\((SB-[0-9A-Za-z]+)\)/.exec((await toastLine.textContent()) ?? '')![1];
  const code = (await (await request.get(`/api/requirements/v1/rq-flows/${flowId}`)).json()).code as string;
  await expect(view).toHaveAttribute('data-status', 'saved');
  await expect(view.locator('h1')).toHaveText('성수 플래그십 리테일 리뉴얼');
  await expect(view.locator('.fl-dver')).toHaveText(`${code} v1`);
  await expect(view.locator('.fl-dhead__meta')).toHaveText(/^오늘 \d\d:\d\d 저장 · 키맨 2 · 요구 5 · 확인 필요 1$/);
  await expect(view.locator('.fl-dnav__label')).toHaveText('단계별 고치기');
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(code);
  await expect(view.locator('.wm-sbbar__chip').first()).toContainText('성수 플래그십 리테일');
  // 사실 칸(보드 View content=rq: 프로젝트명 · 고객사 · 최종 제안대상 · 제작자 의견(고객 문서에서 빠져요) · 읽은 자료)
  const facts = view.locator('.rqv-fact');
  await expect(facts.locator('.rqv-fact__k')).toHaveText(['프로젝트명', '고객사', '최종 제안대상', '제작자 의견· 고객 문서에서 빠져요', '읽은 자료']);
  await expect(facts.locator('.rqv-fact__v')).toHaveText(['성수 플래그십 리테일 리뉴얼', 'K 리츠', '자산관리본부장', '설계 단계 스펙인이 목표', '회의록_K리츠.txt']);
  // 키맨별 요구사항(머리 「키맨 2 · 가중치 합 100%」 · 카드 이름 + 가중치 · 번호 요구 · 확인 필요)
  await expect(view.locator('.rqv-kms__sum')).toHaveText('키맨 2 · 가중치 합 100%');
  await expect(view.locator('.rqv-km__who b')).toHaveText(['자산관리팀장', '마케팅 리드']);
  await expect(view.locator('.rqv-km__w')).toHaveText(['60%', '40%']);
  const mkt = view.locator('[data-vkeyman="마케팅 리드"]');
  await expect(mkt.locator('.rqv-req__t')).toHaveText(['시즌 캠페인 빠른 교체', '방문객 데이터 활용']);
  await expect(mkt.locator('.rqv-req').nth(1).locator('.rqv-req__warn')).toHaveText('확인 필요');
  await expect(view.locator('.rqv-req__warn')).toHaveCount(1);
  // 후속 작업 — DSS(아직 없음 → 만들기 · ?sb=&auto=1)
  const follows = view.locator('a.fl-dnext');
  await expect(follows).toHaveCount(1);
  await expect(follows).toContainText('공간별 제품 매칭 DSS');
  await expect(follows).toContainText(`${sbId}${/[036]$/.test(sbId) ? '으로' : '로'} 공간마다 제품 · 솔루션을 골라요`);
  await expect(follows.locator('.fl-dnext__cta')).toHaveText('만들기');
  await expect(follows).toHaveAttribute('href', `/dss/new?sb=${sbId}&auto=1`);
  // 보드 View(content=rq): 본문 1100 · 왼쪽 340 | 오른쪽 746(1100 − 340 − 14) · 키맨 머리 48 · 키맨 카드 170 | 1fr · 가중치 알약 22 · 후속 카드 1100
  // (y 는 공용 머리 줄(.fl-dhead) 아래 16 — 보드 206, 앱 머리 줄이 55 라 209)
  const bodyY = (await box(view.locator('.fl-dhead'))).y + (await h(view.locator('.fl-dhead'))) + 16;
  expect(await box(view.locator('.rqv'))).toMatchObject({ w: 1100, x: 300, y: bodyY });
  expect(await box(view.locator('.rqv-facts'))).toMatchObject({ w: 340, x: 300, y: bodyY });
  expect(await box(view.locator('.rqv-kms'))).toMatchObject({ w: 746, x: 654, y: bodyY });
  expect(await h(view.locator('.rqv-kms__h'))).toBe(48);
  expect(await w(view.locator('.rqv-km').first())).toBe(712);
  expect(await w(view.locator('.rqv-km__who').first())).toBe(170);
  expect(await h(view.locator('.rqv-km__w').first())).toBe(22);
  expect(await h(view.locator('.rqv-req').first())).toBe(28);
  expect(await box(follows)).toMatchObject({ w: 1100, x: 300 });
  expect(await h(view.getByRole('button', { name: 'flow.json' }))).toBe(38);
  // 허브 flow.json stages.rq · 셀 route 는 이 상세(ContentPopup · Storyboard 화면 링크)
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sbId}`)).json();
  expect(flow.name).toBe('성수 플래그십 리테일');
  expect(flow.stages.rq.target).toBe('자산관리본부장');
  expect(flow.stages.rq.keymen.map((k: { role: string; weight: number }) => [k.role, k.weight])).toEqual([['자산관리팀장', 60], ['마케팅 리드', 40]]);
  expect(flow.stages.rq.requirements[4]).toMatchObject({ text: '방문객 데이터 활용', status: 'check' });
  expect(JSON.stringify(flow.stages.rq)).not.toContain('스펙인');
  expect(flow.cells[0].route).toBe(`/requirements/flow/${flowId}`);
  await page.mouse.move(10, 890);
  await shot(page, 'RQ_View-new');
  await view.getByRole('button', { name: 'flow.json' }).click();
  const json = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(json).toBeVisible();
  await expect(json.getByText('"rq": {').first()).toBeVisible();
  await expect(json.locator('.wm-jsonline--add').first()).toBeVisible();
  await shot(page, 'RQ_ViewJson-new');
  await json.getByRole('button', { name: '닫기' }).last().click();
  await expect(json).toHaveCount(0);

  // 단계 칩 「요구사항 입력」 → 고치기 팝업(RQ1_Edit: RQ-nn v1 고치기 · 저장 · v2 · 목록 링크 없음) — 고치지 않고 닫으면 묻지 않는다
  await view.getByRole('button', { name: /^요구사항 입력 · / }).click();
  await expect(page).toHaveURL(/\?step=input$/);
  const edit = page.locator('.fl-stepdlg');
  await expect(edit.locator('.fl-shead__row b')).toHaveText('성수 플래그십 리테일 리뉴얼');
  await expect(edit.locator('.fl-shead__mode')).toHaveText(`${code} v1 고치기`);
  await expect(edit.locator('.fl-shead__sb')).toContainText('성수 플래그십 리테일');
  await expect(edit.locator('.fl-shead__note')).toHaveText(`저장하면 ${code} v2 · 연결된 Storyboard 1개(${sbId})에 반영돼요`);
  await expect(edit.getByRole('button', { name: '저장 · v2' })).toBeVisible();
  await expect(edit.locator('.wm-flow__back')).toHaveCount(0);
  await expect(edit.locator('#rq-to')).toHaveValue('자산관리본부장');
  await page.mouse.move(10, 890);
  await shot(page, 'RQ1_Edit-new');
  await edit.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(edit).toHaveCount(0);
  await expect(page.getByRole('dialog', { name: '고친 내용을 저장할까요?' })).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/requirements/flow/${flowId}$`));

  // 고친 뒤 닫으면 저장할지 묻는다 → 「저장 · v2」 → 최종본 v2(연결된 Storyboard 에 반영)
  await view.getByRole('button', { name: /^요구사항 입력 · / }).click();
  await edit.locator('#rq-to').fill('대표이사');
  await edit.getByRole('button', { name: '팝업 닫기' }).click();
  const ask = page.getByRole('dialog', { name: '고친 내용을 저장할까요?' });
  await expect(ask).toBeVisible();
  await expect(ask).toContainText(`저장하면 ${code} v2로 연결된 Storyboard에 반영돼요.`);
  await shot(page, 'RQ1_Edit-ask-new');
  await ask.getByRole('button', { name: '저장 · v2' }).click();
  await expect(edit).toHaveCount(0, { timeout: 20_000 });
  await expect(view.locator('.fl-dver')).toHaveText(`${code} v2`);
  await expect(view.locator('.rqv-fact__v').nth(2)).toHaveText('대표이사');
  await expect(page.getByText(`${code} v2 저장 · 연결된 Storyboard 1개에 반영했어요`)).toBeVisible();
  await expect.poll(async () => (await (await request.get(`/api/storyboard/v1/flows/${sbId}`)).json()).stages.rq.target, { timeout: 10_000 }).toBe('대표이사');
  expect((await (await request.get(`/api/storyboard/v1/flows/${sbId}`)).json()).stages.rq.ver).toBe(2);

  // 목록 — 저장한 요구사항 줄(코드 v2 · Storyboard 칩 · 열기 = 이 상세)
  await page.goto('/requirements');
  const row = page.locator('.fl-card').filter({ hasText: `${code} v2` });
  await expect(row).toBeVisible();
  await expect(row.getByRole('button', { name: '성수 플래그십 리테일' })).toBeVisible();
  await expect(row.locator('.fl-cardtitle')).toHaveAttribute('href', `/requirements/flow/${flowId}`);
  await page.mouse.move(10, 890);
  await shot(page, 'RQ0-new');
  // 저장된 것을 열면 최종본만(팝업 없음)
  await row.locator('.fl-cardtitle').click();
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'saved');
  await expect(page.locator('.fl-stepdlg')).toHaveCount(0);
});

test('RQ 새 흐름 — 첫 입력에서 문서가 생겨도 팝업 · 입력이 끊기지 않는다 · 요구 줄 더하기 · 가중치', async ({ page, request }) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `자동 저장 확인 ${Date.now().toString(36)}`;
  await page.goto('/requirements/new');
  const dlg = page.locator('.fl-stepdlg');
  await dlg.locator('#rq-proj').click();
  await page.keyboard.type(name.slice(0, 6));
  await expect(page).toHaveURL(/\/requirements\/flow\/rqf_[0-9A-Za-z]+\?step=input$/, { timeout: 10_000 });
  await page.keyboard.type(name.slice(6));
  await expect(dlg.locator('#rq-proj')).toHaveValue(name);
  await expect(dlg.locator('#rq-proj')).toBeFocused();
  // 키맨 · 요구(엔터로 다음 줄) · 두 번째 키맨 → 가중치 50 : 50 → 첫 키맨 70 → 70 : 30
  await dlg.locator('#rq-k0').fill('대표이사');
  await dlg.locator('.rqf-km').first().getByRole('button', { name: '+ 요구사항' }).click();
  await page.keyboard.type('에너지 사용량 절감');
  await page.keyboard.press('Enter');
  await page.keyboard.type('최초 AI Ready 공간');
  await expect(dlg.getByRole('textbox', { name: '대표이사 요구 2' })).toHaveValue('최초 AI Ready 공간');
  await dlg.getByRole('button', { name: '+ 키맨 추가' }).click();
  await expect(dlg.locator('.rqf-w')).toHaveText(['50%', '50%']);
  await dlg.getByRole('button', { name: /대표이사 가중치 50%/ }).click();
  await dlg.getByRole('textbox', { name: '대표이사 가중치(%)' }).fill('70');
  await page.keyboard.press('Enter');
  await expect(dlg.locator('.rqf-w')).toHaveText(['70%', '30%']);
  const id = new URL(page.url()).pathname.split('/').pop()!;
  await expect.poll(async () => {
    const d = await (await request.get(`/api/requirements/v1/rq-flows/${id}`)).json();
    return [d.title, d.keymen.map((k: { weight: number }) => k.weight), d.keymen[0].reqs.map((r: { text: string }) => r.text)];
  }, { timeout: 10_000 }).toEqual([name, [70, 30], ['에너지 사용량 절감', '최초 AI Ready 공간']]);
  // 새로 읽어도 같은 값(?step=input — 같은 팝업이 열린 채로)
  await page.reload();
  await expect(dlg).toBeVisible();
  await expect(dlg.locator('#rq-proj')).toHaveValue(name);
  await expect(dlg.getByRole('textbox', { name: '대표이사 요구 1' })).toHaveValue('에너지 사용량 절감');
  // 1920 × 1080: 팝업은 가운데 1180 × 800 그대로 · 본문 열 1180 · 고정 칸 400 (UI-W-01 · UI-W-04)
  await page.setViewportSize({ width: 1920, height: 1080 });
  expect(await box(dlg)).toMatchObject({ x: 370, y: 140, w: 1180, h: 800 });
  expect(await widths(page)).toEqual({ flow: 1180, main: 1180, left: 400, right: 684, drop: 1100 });
  // 요구 줄 지우기(번호 자리 ×) · 키맨 빼기(카드 오른쪽 위 ×) → 남은 키맨 100%
  await dlg.getByRole('button', { name: '대표이사 요구 2 지우기' }).click();
  await expect(dlg.getByRole('textbox', { name: '대표이사 요구 2' })).toHaveCount(0);
  await dlg.locator('.rqf-km').nth(1).hover();
  await dlg.getByRole('button', { name: '키맨 2 빼기' }).click();
  await expect(dlg.locator('.rqf-w')).toHaveText(['100%']);
  await expect.poll(async () => {
    const d = await (await request.get(`/api/requirements/v1/rq-flows/${id}`)).json();
    return [d.keymen.length, d.keymen[0].weight, d.keymen[0].reqs.length];
  }, { timeout: 10_000 }).toEqual([1, 100, 1]);
  // 팝업을 닫으면 작성 중 최종본(RQ_Draft: 작성 중 0/1 · ① 자리표시 「이어서 · 요구사항 입력」)
  await page.setViewportSize({ width: 1440, height: 900 });
  await dlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(dlg).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/requirements/flow/${id}$`));
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'draft');
  await expect(view.locator('.fl-dver')).toHaveText('작성 중 0/1');
  await expect(view.locator('h1')).toHaveText(name);
  await expect(view.locator('.fl-dhead__meta')).toHaveText(/^작성 중 · 1단계 중 0단계 마침 · 오늘 \d\d:\d\d · 저장하면 Storyboard가 만들어져요$/);
  await expect(view.locator('.fl-dnav__label')).toHaveText('단계 0/1');
  const cont = view.locator('[data-slot="1"]').getByRole('button', { name: '이어서 · 요구사항 입력' });
  await expect(cont).toBeVisible();
  await expect(view.locator('.rqv')).toHaveCount(0);
  // 보드 RQ_Draft: 자리표시가 본문 남은 높이를 채운다(1100 × 670 · y 206 — 앱은 공용 머리 줄이 3 높아 y 209 · h 667: 아래 끝 876 은 같다)
  const slotY = (await box(view.locator('.fl-dhead'))).y + (await h(view.locator('.fl-dhead'))) + 16;
  expect(await box(view.locator('[data-slot="1"]'))).toMatchObject({ w: 1100, x: 300, y: slotY, h: 876 - slotY });
  await page.mouse.move(10, 890);
  await shot(page, 'RQ_Draft-new');
  await cont.click();
  await expect(page).toHaveURL(/\?step=input$/);
  await expect(dlg.locator('#rq-proj')).toHaveValue(name);
});

test('RQ 새 흐름 — 빈 새 요구사항(보드 RQ1 빈 상태) · 아무것도 적지 않고 닫으면 목록', async ({ page, request }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const before = ((await (await request.get('/api/requirements/v1/rq-flows?limit=100')).json()).items as unknown[]).length;
  await page.goto('/requirements/new');
  const dlg = page.locator('.fl-stepdlg');
  await expect(dlg.getByRole('heading', { name: '고객 요구사항 입력' })).toBeVisible();
  await expect(dlg.locator('#rq-proj')).toHaveValue('');
  await expect(dlg.locator('.rqf-km')).toHaveCount(1);
  await expect(dlg.locator('.rqf-w')).toHaveText(['100%']);
  await expect(dlg.locator('.rqf-chip')).toHaveCount(0);
  await page.mouse.move(10, 890);
  await shot(page, 'RQ1-empty-new');
  // 뒤 최종본: 새로 만들기 · ① 자리표시(다음 단계 · 「이어서」 버튼은 작성 중일 때만)
  await expect(page.locator('.fl-detail [data-slot="1"]')).toHaveClass(/fl-slot--next/);
  await expect(page.locator('.fl-detail [data-slot="1"]').getByRole('button')).toHaveCount(0);
  // 아무것도 적지 않고 닫으면 초안을 만들지 않고 목록으로
  await dlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(page).toHaveURL(/\/requirements$/);
  expect(((await (await request.get('/api/requirements/v1/rq-flows?limit=100')).json()).items as unknown[]).length).toBe(before);
  // Esc 로도 닫힌다
  await page.goto('/requirements/new');
  await expect(dlg).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page).toHaveURL(/\/requirements$/);
});

test('RQ 최종본 — Storyboard 에 DSS 가 이미 있으면 후속 작업은 ref 칩 + 「열기」(그 DSS 로) · 고치기 안내에 연결된 Storyboard', async ({ page, request }) => {
  test.setTimeout(60_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const title = `용산 업무시설 재개발 ${tag()}`;
  const r = await (await request.post('/api/requirements/v1/rq-flows', { data: { title, customer: 'E 자산운용', target: '대표이사',
    keymen: [{ role: '대표이사', weight: 50, reqs: [{ text: '사용자를 인식하고 반응하는 AI Ready 오피스' }, { text: '최초 AI Ready 공간으로 알리기' }] },
      { role: '공간컨텐츠실장', weight: 50, reqs: [{ text: '오피스를 업무환경 플랫폼으로', status: 'check', flag: 'ask' }] }] } })).json();
  const fin = await request.post(`/api/requirements/v1/rq-flows/${r.id}:finish`);
  expect(fin.ok(), await fin.text()).toBeTruthy();
  const sbId = (await fin.json()).sb_id as string;
  const dssRef = `DSS-${tag()}`;
  const put = await request.put(`/api/storyboard/v1/flows/${sbId}/stages/dss`, { headers: internalHeaders('dss'),
    data: { ref: dssRef, ver: 1, value: DSS_VALUE, md: '- 업종: 오피스 · 업무시설 · 공간 3', card: { title: '용산 오피스 공간별 제품', facts: [], groups: [], line: '공간 3 · 제품 6 · 솔루션 2' } } });
  expect(put.ok(), await put.text()).toBeTruthy();
  const cell = ((await (await request.get(`/api/storyboard/v1/flows/${sbId}`)).json()).cells as Array<{ key: string; route: string }>).find((c) => c.key === 'dss')!;

  // 저장된 것을 열면 최종본만(팝업 없음) — 머리 · 사실 칸 · 키맨 카드
  await page.goto(`/requirements/flow/${r.id}`);
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'saved');
  await expect(page.locator('.fl-stepdlg')).toHaveCount(0);
  await expect(view.locator('.fl-dver')).toHaveText(`${r.code} v1`);
  await expect(view.locator('.fl-dhead__meta')).toHaveText(/ · 키맨 2 · 요구 3 · 확인 필요 1$/);
  await expect(view.locator('.rqv-fact__v').nth(3)).toHaveText('적지 않았어요');
  await expect(view.locator('.rqv-fact__v').nth(4)).toHaveText('직접 입력');
  await expect(view.locator('.rqv-kms__sum')).toHaveText('키맨 2 · 가중치 합 100%');
  await expect(view.locator('[data-vkeyman="공간컨텐츠실장"] .rqv-req__warn')).toHaveText('확인 필요');
  // 후속 작업 DSS — 이미 있으니 ref 칩 · 「열기」 · 그 DSS 상세로 · 설명은 그 DSS 의 수
  const next = view.locator('a.fl-dnext');
  await expect(next).toHaveCount(1);
  await expect(next.locator('.fl-dnext__ref')).toHaveText(`${dssRef} v1`);
  await expect(next.locator('.fl-dnext__cta')).toHaveText('열기');
  await expect(next).toContainText('공간 3 · 제품 6 · 솔루션 2');
  await expect(next).toHaveAttribute('href', cell.route);
  await expect(view.locator('.wm-sbbar__stage').first()).toHaveText('DSS까지');
  // 고치기 팝업 — 직접 입력이면 「직접 입력 · 읽은 자료 없음」(보드 RQ1_Edit)
  await view.getByRole('button', { name: /^요구사항 입력 · / }).click();
  const edit = page.locator('.fl-stepdlg');
  await expect(edit.locator('.fl-shead__note')).toHaveText(`저장하면 ${r.code} v2 · 연결된 Storyboard 1개(${sbId})에 반영돼요`);
  await expect(edit.locator('.rqf-chip')).toHaveText('직접 입력 · 읽은 자료 없음');
  await page.keyboard.press('Escape');
  await expect(edit).toHaveCount(0);
});
