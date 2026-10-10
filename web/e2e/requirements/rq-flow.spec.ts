/**
 * 고객 요구사항 새 흐름(2026-10-08 보드 webapp1 RQ0 · RQ1 · RQ1_AI · RQ_Done) — 실제 스택(mock 모델 · mocks/ai-tools/rq.flow_extract.v1 · rq.deep_questions.v1).
 * 목록 → 새 요구사항(바로 RQ1) → 파일로 채우기 → 직접 입력 → AI 심층 질의(폼에 반영 · 고객에게 확인) → 저장 → 완료(Storyboard 자동 생성).
 * 보드의 고정 칸 폭(400 · 300 · 380 · 본문 1180 · 800)을 숫자로 재고, 화면을 __screens__/<보드>-new.png 로 남긴다.
 * 실행: make e2e-feature SERVICE=requirements (1 worker)
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { shot } from './helpers';

const K_MEMO = `K 리츠 미팅 회의록 — 성수 플래그십 리테일 리뉴얼
참석: 자산관리팀장, 마케팅 리드
- 자산관리팀장: 1층 파사드 미디어로 집객, 테넌트별 콘텐츠 운영, 시설 원격 관리
- 마케팅 리드: 시즌 캠페인 빠른 교체, 방문객 데이터 활용
`;

const w = async (l: Locator) => Math.round((await l.boundingBox())!.width);
const h = async (l: Locator) => Math.round((await l.boundingBox())!.height);

async function widths(page: Page) {
  return {
    flow: await w(page.locator('.wm-flow')),
    main: await w(page.locator('.rqf-main')),
    left: await w(page.locator('.rqf-left')),
    right: await w(page.locator('.rqf-right')),
    drop: await w(page.locator('.rqf-drop')),
  };
}

test('RQ 새 흐름 — 목록 · 입력 · 파일 · AI 심층 질의 · 저장 · Storyboard 자동 생성', async ({ page, request }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1440, height: 900 });

  // RQ0 — 목록(보드 List content=rq)
  await page.goto('/requirements');
  await expect(page.getByRole('heading', { name: '고객 요구사항', exact: true })).toBeVisible();
  await expect(page.getByText('가장 첫 단위예요. 저장하면 Storyboard가 자동으로 만들어져요.')).toBeVisible();
  await page.getByRole('link', { name: '새 요구사항' }).first().click();

  // RQ1 — 사전 작업이 없어 Gate 없이 바로 폼
  await expect(page).toHaveURL(/\/requirements\/new$/);
  await expect(page.getByRole('heading', { name: '고객 요구사항 입력' })).toBeVisible();
  await expect(page.getByText('저장하면 이 요구사항으로 Storyboard가 자동으로 만들어져요')).toBeVisible();
  await expect(page.getByText('모두 선택 항목이에요')).toBeVisible();
  // 보드 RQ1: 본문 열 1180 · 왼쪽 400 | 오른쪽 1fr(1180 − 80 − 400 − 16 = 684) · 끌어 놓기 줄 1100×64 · 버튼 40 · 입력 42 · 저장 48
  expect(await widths(page)).toEqual({ flow: 1180, main: 1180, left: 400, right: 684, drop: 1100 });
  expect(await h(page.locator('.rqf-drop'))).toBe(64);
  expect(await h(page.getByRole('button', { name: 'AI 심층 질의로 폼 완성' }))).toBe(40);
  expect(await h(page.locator('#rq-proj'))).toBe(42);
  expect(await h(page.getByRole('button', { name: '저장', exact: true }))).toBe(48);
  expect(await h(page.locator('.rqf-role').first())).toBe(34);
  expect(await h(page.locator('.rqf-w').first())).toBe(28);

  // 파일 첨부 → 문서가 생기고(주소 /requirements/flow/rqf_…) 잡이 빈 칸을 채운다(mock: 회의록 K 리츠)
  await page.locator('input[type=file][aria-label="파일 첨부"]').setInputFiles({ name: '회의록_K리츠.txt', mimeType: 'text/plain', buffer: Buffer.from(K_MEMO) });
  await expect(page).toHaveURL(/\/requirements\/flow\/rqf_[0-9A-Za-z]+$/, { timeout: 15_000 });
  await expect(page.locator('.rqf-chip')).toHaveText('회의록_K리츠.txt에서 읽음', { timeout: 30_000 });
  await expect(page.locator('#rq-proj')).toHaveValue('성수 플래그십 리테일 리뉴얼');
  await expect(page.locator('#rq-cust')).toHaveValue('K 리츠');
  await expect(page.locator('#rq-to')).toHaveValue('');
  await expect(page.locator('#rq-to')).toHaveAttribute('placeholder', '예) 대표이사');
  await expect(page.locator('#rq-k0')).toHaveValue('자산관리팀장');
  await expect(page.locator('#rq-k1')).toHaveValue('마케팅 리드');
  await expect(page.locator('.rqf-w')).toHaveText(['60%', '40%']);
  await expect(page.getByRole('textbox', { name: '마케팅 리드 요구 2' })).toHaveValue('방문객 데이터 활용');
  await expect(page.locator('[data-req]').nth(4).locator('.rqf-tag--vague')).toHaveText('범위 불명확');
  await expect(page.getByText('가중치 합 100%')).toBeVisible();
  const flowId = page.url().split('/').pop()!;

  // 직접 입력 — 제작자 의견(고객 문서 · Storyboard 에서 빠진다) · 자동 저장
  await page.locator('#rq-note').fill('설계 단계 스펙인이 목표');
  await expect.poll(async () => (await (await request.get(`/api/requirements/v1/rq-flows/${flowId}`)).json()).note, { timeout: 10_000 }).toBe('설계 단계 스펙인이 목표');
  await page.locator('#rq-note').fill('');
  await expect.poll(async () => (await (await request.get(`/api/requirements/v1/rq-flows/${flowId}`)).json()).note, { timeout: 10_000 }).toBe('');
  await page.locator('#rq-note').blur();
  await page.mouse.move(10, 890);
  await shot(page, 'RQ1-new');

  // RQ1_AI — AI 심층 질의(누를 때만 열린다 · 380px) · 본문 800 · 왼쪽 300
  await page.getByRole('button', { name: 'AI 심층 질의로 폼 완성' }).click();
  const ai = page.getByRole('complementary', { name: 'AI 심층 질의' });
  await expect(ai.getByText('최종 제안대상이 비어 있어요. 누구에게 최종 제안하나요?')).toBeVisible({ timeout: 20_000 });
  await expect(ai.getByText('폼에서 부족한 곳 3개를 찾았어요 · 답하면 폼에 바로 반영돼요')).toBeVisible();
  await expect(ai.getByLabel('진행')).toHaveText('1 / 3');
  await expect(page.getByRole('button', { name: 'AI 심층 질의로 폼 완성' })).toHaveCount(0);
  expect(await w(ai)).toBe(380);
  expect(await widths(page)).toEqual({ flow: 1180, main: 800, left: 300, right: 424, drop: 740 });
  await expect(ai.getByRole('button', { name: '대표이사' })).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'RQ1_AI-new');

  // 1) 보기 고르기 → 폼에 반영(ai-accepted · 초록)
  await ai.getByRole('button', { name: '자산관리본부장' }).click();
  await expect(ai.getByRole('button', { name: '자산관리본부장' })).toHaveAttribute('aria-pressed', 'true');
  await ai.getByRole('button', { name: '폼에 반영' }).click();
  await expect(page.locator('#rq-to')).toHaveValue('자산관리본부장');
  await expect(page.locator('#rq-to')).toHaveClass(/rqf-input--ai/);
  await expect(page.locator('label[for="rq-to"]')).toContainText('AI 질의로 채움');
  // 2) 고객에게 확인으로 남기기 → 요구 꼬리표 「고객에게 확인」
  await expect(ai.getByLabel('진행')).toHaveText('2 / 3');
  await expect(ai.getByText('‘방문객 데이터 활용’은 어디까지인가요?')).toBeVisible();
  await ai.getByRole('button', { name: '고객에게 확인으로 남기기' }).click();
  await expect(page.locator('[data-req]').nth(4).locator('.rqf-tag--ask')).toHaveText('고객에게 확인');
  // 3) 가중치 — 맞아요 · 60 : 40 → 알약이 초록(AI 질의로 확인)
  await expect(ai.getByLabel('진행')).toHaveText('3 / 3');
  await ai.getByRole('button', { name: '맞아요 · 60 : 40' }).click();
  await ai.getByRole('button', { name: '폼에 반영' }).click();
  await expect(ai.getByText('질의를 마쳤어요')).toBeVisible();
  await expect(ai.getByText('2개를 폼에 반영했고, 1개는 고객에게 확인으로 남겼어요.')).toBeVisible();
  await expect(page.locator('.rqf-w.rqf-w--ai')).toHaveCount(2);
  await page.mouse.move(10, 890);
  await shot(page, 'RQ1_AI-done-new');
  await ai.getByRole('button', { name: '닫기' }).last().click();
  await expect(ai).toHaveCount(0);

  // 저장 → RQ_Done(보드 Done content=rq) · Storyboard 자동 생성
  await page.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByRole('heading', { name: '요구사항을 저장했어요' })).toBeVisible({ timeout: 20_000 });
  const sub = page.getByText(/Storyboard ‘성수 플래그십 리테일’\((SB-[0-9A-Za-z]+)\)[이가] 자동으로 만들어졌어요/);
  await expect(sub).toBeVisible();
  const sbId = /\((SB-[0-9A-Za-z]+)\)/.exec((await sub.textContent()) ?? '')![1];
  await expect(page.getByText(/"stages\.rq": \{/)).toBeVisible();
  await expect(page.locator('.wm-done__md pre')).toContainText('마케팅 리드(40%): 시즌 캠페인 빠른 교체 · 방문객 데이터 활용 [확인 필요]');
  await expect(page.locator('a.wm-follow')).toContainText('공간별 제품 매칭 DSS');
  await expect(page.locator('a.wm-follow')).toHaveAttribute('href', `/dss/new?sb=${sbId}&auto=1`);
  await expect(page.getByText(`${sbId}${/[036]$/.test(sbId) ? '으로' : '로'} 공간마다 제품 · 솔루션을 골라요`)).toBeVisible();
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sbId}`)).json();
  expect(flow.name).toBe('성수 플래그십 리테일');
  expect(flow.stages.rq.target).toBe('자산관리본부장');
  expect(flow.stages.rq.keymen.map((k: { role: string; weight: number }) => [k.role, k.weight])).toEqual([['자산관리팀장', 60], ['마케팅 리드', 40]]);
  expect(flow.stages.rq.requirements[4]).toMatchObject({ text: '방문객 데이터 활용', status: 'check' });
  expect(JSON.stringify(flow.stages.rq)).not.toContain('스펙인');
  expect(flow.cells[0].route).toBe(`/requirements/flow/${flowId}`);
  // 보드 Done: 본문 좌우 80 → 카드 1020 · 요약 · JSON 상자 248 + 선(그려진 높이 250) · 후속 작업 카드 84
  expect(await w(page.locator('.wm-done__card'))).toBe(1020);
  expect(await h(page.locator('.wm-done__md'))).toBe(250);
  expect(await h(page.locator('.wm-follow'))).toBe(84);
  await page.mouse.move(10, 890);
  await shot(page, 'RQ_Done-new');
  await page.getByRole('button', { name: '전체 JSON 보기' }).click();
  const dlg = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByText('"rq": {').first()).toBeVisible();
  await shot(page, 'RQ_DoneJson-new');
  await dlg.getByRole('button', { name: '닫기' }).last().click();

  // 다시 고치기 → 같은 문서(코드 · ver 1) · 목록에 Storyboard 칩
  await page.getByRole('button', { name: '다시 고치기' }).click();
  await expect(page.locator('#rq-to')).toHaveValue('자산관리본부장');
  await expect(page.locator('.wm-sbbar__chip')).toContainText('성수 플래그십 리테일');
  const code = (await (await request.get(`/api/requirements/v1/rq-flows/${flowId}`)).json()).code as string;
  await page.getByRole('link', { name: '목록' }).click();
  await expect(page).toHaveURL(/\/requirements$/);
  const row = page.getByRole('row').filter({ hasText: `${code} v1` });
  await expect(row).toBeVisible();
  await expect(row.getByRole('button', { name: '성수 플래그십 리테일' })).toBeVisible();
  await page.mouse.move(10, 890);
  await shot(page, 'RQ0-new');
});

test('RQ 새 흐름 — 첫 입력에서 문서가 생겨도 입력이 끊기지 않는다 · 요구 줄 더하기 · 가중치', async ({ page, request }) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `자동 저장 확인 ${Date.now().toString(36)}`;
  await page.goto('/requirements/new');
  await page.locator('#rq-proj').click();
  await page.keyboard.type(name.slice(0, 6));
  await expect(page).toHaveURL(/\/requirements\/flow\/rqf_/, { timeout: 10_000 });
  await page.keyboard.type(name.slice(6));
  await expect(page.locator('#rq-proj')).toHaveValue(name);
  await expect(page.locator('#rq-proj')).toBeFocused();
  // 키맨 · 요구(엔터로 다음 줄) · 두 번째 키맨 → 가중치 50 : 50 → 첫 키맨 70 → 70 : 30
  await page.locator('#rq-k0').fill('대표이사');
  await page.locator('.rqf-km').first().getByRole('button', { name: '+ 요구사항' }).click();
  await page.keyboard.type('에너지 사용량 절감');
  await page.keyboard.press('Enter');
  await page.keyboard.type('최초 AI Ready 공간');
  await expect(page.getByRole('textbox', { name: '대표이사 요구 2' })).toHaveValue('최초 AI Ready 공간');
  await page.getByRole('button', { name: '+ 키맨 추가' }).click();
  await expect(page.locator('.rqf-w')).toHaveText(['50%', '50%']);
  await page.getByRole('button', { name: /대표이사 가중치 50%/ }).click();
  await page.getByRole('textbox', { name: '대표이사 가중치(%)' }).fill('70');
  await page.keyboard.press('Enter');
  await expect(page.locator('.rqf-w')).toHaveText(['70%', '30%']);
  const id = page.url().split('/').pop()!;
  await expect.poll(async () => {
    const d = await (await request.get(`/api/requirements/v1/rq-flows/${id}`)).json();
    return [d.title, d.keymen.map((k: { weight: number }) => k.weight), d.keymen[0].reqs.map((r: { text: string }) => r.text)];
  }, { timeout: 10_000 }).toEqual([name, [70, 30], ['에너지 사용량 절감', '최초 AI Ready 공간']]);
  // 새로 읽어도 같은 값
  await page.reload();
  await expect(page.locator('#rq-proj')).toHaveValue(name);
  await expect(page.getByRole('textbox', { name: '대표이사 요구 1' })).toHaveValue('에너지 사용량 절감');
  // 1920 폭에서도 본문 열은 1180 · 고정 칸 400 (UI-W-01 · UI-W-04)
  await page.setViewportSize({ width: 1920, height: 1080 });
  expect(await widths(page)).toEqual({ flow: 1180, main: 1180, left: 400, right: 684, drop: 1100 });
  // 요구 줄 지우기(번호 자리 ×) · 키맨 빼기(카드 오른쪽 위 ×) → 남은 키맨 100%
  await page.getByRole('button', { name: '대표이사 요구 2 지우기' }).click();
  await expect(page.getByRole('textbox', { name: '대표이사 요구 2' })).toHaveCount(0);
  await page.locator('.rqf-km').nth(1).hover();
  await page.getByRole('button', { name: '키맨 2 빼기' }).click();
  await expect(page.locator('.rqf-w')).toHaveText(['100%']);
  await expect.poll(async () => {
    const d = await (await request.get(`/api/requirements/v1/rq-flows/${id}`)).json();
    return [d.keymen.length, d.keymen[0].weight, d.keymen[0].reqs.length];
  }, { timeout: 10_000 }).toEqual([1, 100, 1]);
});

test('RQ 새 흐름 — 빈 새 요구사항(보드 RQ1 빈 상태)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/requirements/new');
  await expect(page.getByRole('heading', { name: '고객 요구사항 입력' })).toBeVisible();
  await expect(page.locator('#rq-proj')).toHaveValue('');
  await expect(page.locator('.rqf-km')).toHaveCount(1);
  await expect(page.locator('.rqf-w')).toHaveText(['100%']);
  await expect(page.locator('.rqf-chip')).toHaveCount(0);
  await page.mouse.move(10, 890);
  await shot(page, 'RQ1-empty-new');
  // 아무것도 적지 않고 떠나면 초안을 만들지 않는다
  await page.getByRole('link', { name: '목록' }).click();
  await expect(page).toHaveURL(/\/requirements$/);
});
