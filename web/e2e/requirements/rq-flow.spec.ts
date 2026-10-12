/**
 * 고객 요구사항 v63 — 상세는 최종본 한 장(보드 webapp1 RQ1 · RQ_Draft · RQ_View · RQ1_Edit · 본문 RQBody) — 실제 스택(mock 모델 · mocks/ai-tools/rq.flow_extract.v1).
 * 목록 → 「새 요구사항 만들기」(팝업 없이 바로 빈 최종본) → 바로 입력(칸을 떠나면 저장 · 첫 입력에 초안 · 주소 /flow/:id) → 저장(Storyboard 자동 생성)
 * → 같은 화면이 저장됨 → 한 칸 고치기 → 「고친 곳 1」 → 되돌리기 → 다시 고쳐 저장 · v2. 파일 첨부는 빈 칸만 채운다.
 * 보드의 고정 칸 폭(340 · 176 · 본문 1100 · 1180)을 숫자로 재고, 화면을 __screens__/<보드>.png 로 남긴다(_rendered 와 나란히 본다).
 * 실행: make e2e-feature SERVICE=requirements (1 worker)
 */
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { shot } from './helpers';

const K_MEMO = `K 리츠 미팅 회의록 — 성수 플래그십 리테일 리뉴얼
참석: 자산관리팀장, 마케팅 리드
- 자산관리팀장: 1층 파사드 미디어로 집객, 테넌트별 콘텐츠 운영, 시설 원격 관리
- 마케팅 리드: 시즌 캠페인 빠른 교체, 방문객 데이터 활용
`;

const box = async (l: Locator) => (await l.boundingBox())!;
const w = async (l: Locator) => Math.round((await box(l)).width);
const h = async (l: Locator) => Math.round((await box(l)).height);
const y = async (l: Locator) => Math.round((await box(l)).y);
const bottom = async (l: Locator) => { const b = await box(l); return Math.round(b.y + b.height); };
const tb = (page: Page, name: string) => page.getByRole('textbox', { name, exact: true });
const rf = async (request: APIRequestContext, id: string) => (await request.get(`/api/requirements/v1/rq-flows/${id}`)).json();

/** 칸에 쓰고 떠나기(InlineInput 은 떠날 때 한 번 저장) */
async function put(l: Locator, v: string) {
  await l.fill(v);
  await l.blur();
}

/** 보드 RQBody · View 고정 칸(1440×900): 본문 열 1180 · 본문 1100(좌우 40) · 개요 340 | 키맨 1fr(1100 − 340 − 14 = 746) · 키맨 이름 176 */
async function widths(page: Page) {
  return {
    flow: await w(page.locator('.wm-flow.cd')),
    body: await w(page.locator('.rqb')),
    ov: await w(page.locator('.rqb-ov')),
    km: await w(page.locator('.rqb-kmcard')),
    drop: await w(page.locator('.rqb-drop')),
    name: await w(page.locator('.rqb-name').first()),
  };
}

const BOARD_W = { flow: 1180, body: 1100, ov: 340, km: 746, drop: 1100, name: 176 };

test('RQ v63 — 목록 · 빈 최종본에 바로 입력 · 저장 · 저장됨 · 고친 곳 1 · 되돌리기 · v2', async ({ page, request }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `용산 업무시설 ${Date.now().toString(36).slice(-4)}`;

  // RQ0 — 목록(보드 List content=rq) → 「새 요구사항 만들기」
  await page.goto('/requirements');
  await expect(page.getByRole('heading', { name: '고객 요구사항', exact: true })).toBeVisible();
  await page.getByRole('link', { name: /새 요구사항 만들기/ }).click();

  // RQ1 — 팝업 없이 바로 빈 최종본(보드 RQ1 · RQBody new)
  await expect(page).toHaveURL(/\/requirements\/new$/);
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: '새 요구사항', level: 1 })).toBeVisible();
  await expect(page.locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(page.locator('.cd-meta')).toHaveText('새로 만드는 중 · 쓰는 대로 작성 중으로 남아요 · 저장하면 이 요구사항으로 Storyboard가 만들어져요');
  await expect(page.getByText('저장하면 이 요구사항으로 Storyboard가 자동으로 만들어져요')).toBeVisible();
  await expect(page.getByRole('button', { name: '저장 · Storyboard 만들기' })).toBeVisible();
  await expect(page.locator('.rqb-drop__t')).toHaveText('파일을 끌어다 놓으면 빈 칸이 채워져요 · PPTX · PDF · DOCX · 메일');
  await expect(page.locator('.rqb-read')).toHaveText('아직 읽은 자료 없음');
  await expect(page.locator('.rqb-sum')).toHaveText('키맨 1 · 요구 0 · 가중치 합 100%');
  await expect(page.getByText('모두 선택 항목이에요 · 비어 있어도 저장돼요')).toBeVisible();
  await expect(tb(page, '키맨 1 가중치(%)')).toHaveValue('100');
  await expect(tb(page, '키맨 1 요구사항 1')).toHaveAttribute('placeholder', '요구사항 · 예) 에너지 사용량 20% 절감');
  await expect(page.locator('.cd-next')).toHaveCount(0);
  // 보드 고정 칸 · 높이(새로 만들기: 파일 띠 60 · 위 196 → 그리드 268 · 아래 878)
  expect(await widths(page)).toEqual(BOARD_W);
  expect([await y(page.locator('.rqb-drop')), await h(page.locator('.rqb-drop'))]).toEqual([196, 60]);
  expect([await y(page.locator('.rqb-ov')), await bottom(page.locator('.rqb-ov'))]).toEqual([268, 878]);
  expect(await h(page.locator('.rqb-kmhead'))).toBe(50);
  expect(await h(tb(page, '프로젝트명'))).toBe(38);
  expect([await w(tb(page, '키맨 1 가중치(%)')), await h(tb(page, '키맨 1 가중치(%)'))]).toEqual([52, 28]);
  expect(await h(page.locator('.rqb-name').first())).toBe(34);
  expect(await h(tb(page, '키맨 1 요구사항 1'))).toBe(32);
  expect(await h(page.locator('.cd-head'))).toBe(46);
  // 들어오기만 해서는 초안을 만들지 않는다
  const before = (await (await request.get('/api/requirements/v1/rq-flows?limit=200')).json()).items.length;
  await page.mouse.move(10, 890);

  // 바로 입력 — 첫 칸을 떠나면 초안이 생기고 주소가 /flow/:id (화면은 그대로 「새로 만들기」)
  await put(tb(page, '프로젝트명'), name);
  await expect(page).toHaveURL(/\/requirements\/flow\/rqf_[0-9A-Za-z]+$/, { timeout: 15_000 });
  const id = page.url().split('/').pop()!;
  expect((await (await request.get('/api/requirements/v1/rq-flows?limit=200')).json()).items.length).toBe(before + 1);
  await expect(page.locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(tb(page, '프로젝트명')).toHaveValue(name);
  await expect(tb(page, '프로젝트명')).toHaveClass(/rqb-f--b/);
  await put(tb(page, '고객사'), 'E 자산운용');
  await put(tb(page, '키맨 1'), '대표이사');
  // 요구 줄: 쓰고 Enter → 아래에 새 줄(포커스) · 두 번째 키맨 더하기(남은 몫 0 → 합 노란색)
  await tb(page, '대표이사 요구사항 1').fill('사용자를 인식하고 반응하는 AI Ready 오피스');
  await page.keyboard.press('Enter');
  await expect(tb(page, '대표이사 요구사항 2')).toBeFocused();
  await page.keyboard.type('최초 AI Ready 공간으로 알리기');
  await page.keyboard.press('Tab');
  await page.getByRole('button', { name: '+ 키맨 추가' }).click();
  await expect(tb(page, '키맨 2')).toBeFocused();
  await page.keyboard.type('공간컨텐츠실장');
  await page.keyboard.press('Tab');
  await expect(page.locator('.rqb-sum')).toHaveText('키맨 2 · 요구 2 · 가중치 합 100%');
  await put(tb(page, '공간컨텐츠실장 가중치(%)'), '30');
  await expect(page.locator('.rqb-sum')).toHaveText('키맨 2 · 요구 2 · 가중치 합 130%');
  await expect(page.locator('.rqb-sum')).toHaveClass(/rqb-sum--warn/);
  await put(tb(page, '대표이사 가중치(%)'), '70');
  await expect(page.locator('.rqb-sum')).not.toHaveClass(/rqb-sum--warn/);
  await put(tb(page, '공간컨텐츠실장 요구사항 1'), '오피스를 업무환경 플랫폼으로');
  // 확인 필요로 표시(줄에 손을 올리면) → 노란 꼬리표
  await page.locator('.rqb-req').filter({ has: tb(page, '공간컨텐츠실장 요구사항 1') }).hover();
  await page.getByRole('button', { name: '공간컨텐츠실장 요구사항 1 확인 필요로 표시' }).click();
  await expect(page.locator('.rqb-tag--warn')).toHaveText(['확인 필요']);
  await expect.poll(async () => {
    const d = await rf(request, id);
    return [d.title, d.customer, d.keymen.map((k: { role: string; weight: number }) => `${k.role}:${k.weight}`), d.counts.reqs, d.counts.check, d.ver, d.changes];
  }, { timeout: 10_000 }).toEqual([name, 'E 자산운용', ['대표이사:70', '공간컨텐츠실장:30'], 3, 1, 0, 0]);
  // 저장 전에는 고친 칸 표시가 없다
  await expect(page.locator('.cd-in--chg')).toHaveCount(0);

  // 저장 → 첫 저장에 Storyboard 자동 생성 · 같은 화면이 저장됨(보드 RQ_View)
  await page.getByRole('button', { name: '저장 · Storyboard 만들기' }).click();
  const toastSb = page.locator('.wm-toast').filter({ hasText: /Storyboard ‘.+’\((SB-[0-9A-Za-z]+)\)[이가] 만들어졌어요/ });
  await expect(toastSb).toBeVisible({ timeout: 20_000 });
  const sbId = /\((SB-[0-9A-Za-z]+)\)/.exec((await toastSb.textContent()) ?? '')![1];
  const code = (await rf(request, id)).code as string;
  await expect(toastSb).toContainText(`${code} v1 저장`);
  await expect(page).toHaveURL(new RegExp(`/requirements/flow/${id}$`));
  await expect(page.getByRole('heading', { name, level: 1 })).toBeVisible();
  await expect(page.locator('.cd-ref')).toHaveText(`${code} v1`);
  await expect(page.locator('.cd-meta')).toHaveText(/^오늘 \d\d:\d\d 저장 · 키맨 2 · 요구 3 · 확인 필요 1$/);
  await expect(page.getByText('눌러서 바로 고쳐요')).toBeVisible();
  await expect(page.getByRole('button', { name: /저장/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /flow\.json/ })).toBeVisible();
  await expect(page.locator('.wm-sbbar__chip')).toHaveCount(1);
  await expect(page.locator('.rqb-drop__t')).toHaveText('파일을 더 놓으면 빈 칸만 채워요 · PPTX · PDF · DOCX · 메일');
  await expect(page.locator('.rqb-read')).toHaveText('직접 입력');
  // 후속 작업 — Storyboard 에 DSS 가 아직 없으면 사전 작업 고르기 없이 새로 만들기
  const next = page.locator('a.cd-nextcard');
  await expect(next).toHaveCount(1);
  await expect(next).toContainText('공간별 제품 매칭 DSS');
  await expect(next).toContainText('만들기');
  await expect(next).toHaveAttribute('href', `/dss/new?sb=${sbId}&auto=1`);
  // 저장됨 높이(보드 View bodyH 562: 파일 띠 46 · 그리드 254 → 758 · 후속 작업 카드 76)
  expect(await widths(page)).toEqual(BOARD_W);
  expect([await y(page.locator('.rqb-drop')), await h(page.locator('.rqb-drop'))]).toEqual([196, 46]);
  expect([await y(page.locator('.rqb-ov')), await bottom(page.locator('.rqb-ov'))]).toEqual([254, 758]);
  expect(await h(next)).toBe(76);
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sbId}`)).json();
  expect(flow.stages.rq.ref).toBe(code);
  expect(flow.stages.rq.keymen.map((k: { role: string; weight: number }) => [k.role, k.weight])).toEqual([['대표이사', 70], ['공간컨텐츠실장', 30]]);
  expect(flow.cells[0].route).toBe(`/requirements/flow/${id}`);

  // flow.json 팝업(이 콘텐츠 줄 강조)
  await page.getByRole('button', { name: /flow\.json/ }).click();
  const dlg = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByText('"rq": {').first()).toBeVisible();
  await dlg.getByRole('button', { name: '닫기' }).last().click();
  await expect(dlg).toHaveCount(0);

  // 한 칸 고치기 → 「고친 곳 1」(보드 RQ1_Edit) · 고친 칸 cd-in--chg + 「고침」
  await put(tb(page, '대표이사 요구사항 2'), '국내 최초 AI Ready 오피스로 알리기');
  await expect(page.locator('.cd-chg')).toHaveText('고친 곳 1', { timeout: 10_000 });
  await expect(page.locator('.cd-ref')).toHaveText(`${code} v1 · 고치는 중`);
  await expect(page.locator('.cd-meta')).toHaveText(`${code} v1 고치는 중 · 저장하면 v2 · ${sbId}에 반영돼요`);
  await expect(page.getByText('저장하면 반영돼요')).toBeVisible();
  await expect(tb(page, '대표이사 요구사항 2')).toHaveClass(/cd-in--chg/);
  await expect(page.locator('.rqb-req').filter({ has: tb(page, '대표이사 요구사항 2') }).locator('.rqb-tag--chg')).toHaveText('고침');
  await expect(page.getByRole('button', { name: '저장 · v2' })).toBeVisible();
  expect((await rf(request, id)).changes).toBe(1);
  expect((await (await request.get(`/api/storyboard/v1/flows/${sbId}`)).json()).stages.rq.requirements[1].text).toBe('최초 AI Ready 공간으로 알리기');

  // 되돌리기 → 저장한 판(changes 0) · 표시 지움
  await page.getByRole('button', { name: '되돌리기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: `${code} v1로 되돌렸어요` })).toBeVisible();
  await expect(tb(page, '대표이사 요구사항 2')).toHaveValue('최초 AI Ready 공간으로 알리기');
  await expect(page.locator('.cd-chg')).toHaveCount(0);
  await expect(page.locator('.cd-in--chg, .rqb-tag--chg')).toHaveCount(0);
  await expect(page.getByText('눌러서 바로 고쳐요')).toBeVisible();
  expect((await rf(request, id)).changes).toBe(0);

  // 다시 고쳐(최종 제안대상 · 요구 하나 더) 저장 → v2 · 같은 Storyboard 에 반영
  await put(tb(page, '최종 제안대상'), '대표이사');
  await expect(tb(page, '최종 제안대상')).toHaveClass(/cd-in--chg/);
  await expect(page.locator('[data-field="target"] .rqb-tag--chg')).toHaveText('새로 씀');
  await page.locator('[data-keyman]').nth(1).getByRole('button', { name: '+ 요구사항' }).click();
  await expect(tb(page, '공간컨텐츠실장 요구사항 2')).toBeFocused();
  await page.keyboard.type('예측 · 반응형 공간');
  await page.keyboard.press('Tab');
  await expect(page.locator('.cd-chg')).toHaveText('고친 곳 2', { timeout: 10_000 });
  await expect(page.locator('.rqb-req').filter({ has: tb(page, '공간컨텐츠실장 요구사항 2') }).locator('.rqb-tag--chg')).toHaveText('새로 씀');
  await page.getByRole('button', { name: '저장 · v2' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: `${code} v2 저장 · Storyboard ‘` })).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.cd-ref')).toHaveText(`${code} v2`);
  await expect(page.locator('.cd-chg')).toHaveCount(0);
  await expect(page.locator('.cd-in--chg')).toHaveCount(0);
  const flow2 = await (await request.get(`/api/storyboard/v1/flows/${sbId}`)).json();
  expect([flow2.stages.rq.ver, flow2.stages.rq.target, flow2.stages.rq.counts.reqs]).toEqual([2, '대표이사', 4]);
  const d2 = await rf(request, id);
  expect([d2.ver, d2.changes, d2.sb_ids]).toEqual([2, 0, [sbId]]);

  // 목록 — 완성 카드(코드 v2 · Storyboard 칩)
  await page.goto('/requirements');
  const card = page.locator('.fl-card').filter({ hasText: `${code} v2` });
  await expect(card).toBeVisible();
  await card.getByRole('link', { name }).click();
  await expect(page).toHaveURL(new RegExp(`/requirements/flow/${id}$`));
  await expect(page.locator('.cd-ref')).toHaveText(`${code} v2`);
});

test('RQ v63 — 파일 첨부는 빈 칸만 채운다 · 다시 열면 작성 중(보드 RQ_Draft)', async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/requirements/new');
  await expect(page.locator('.cd-ref')).toHaveText('새로 만들기');
  // 사람이 먼저 쓴 값(고객사)은 덮지 않는다
  await put(tb(page, '고객사'), 'K 리츠');
  await expect(page).toHaveURL(/\/requirements\/flow\/rqf_/, { timeout: 15_000 });
  const id = page.url().split('/').pop()!;
  await page.locator('input[type=file][aria-label="파일 첨부"]').setInputFiles({ name: '회의록_K리츠.txt', mimeType: 'text/plain', buffer: Buffer.from(K_MEMO) });
  await expect(page.locator('.rqb-read')).toHaveText('회의록_K리츠.txt에서 읽음', { timeout: 30_000 });
  await expect(page.locator('.rqb-read')).toHaveClass(/rqb-read--src/);
  await expect(tb(page, '프로젝트명')).toHaveValue('성수 플래그십 리테일 리뉴얼');
  await expect(tb(page, '고객사')).toHaveValue('K 리츠');
  await expect(tb(page, '최종 제안대상')).toHaveValue('');
  await expect(tb(page, '키맨 1')).toHaveValue('자산관리팀장');
  await expect(tb(page, '키맨 2')).toHaveValue('마케팅 리드');
  await expect(tb(page, '자산관리팀장 가중치(%)')).toHaveValue('60');
  await expect(tb(page, '마케팅 리드 요구사항 2')).toHaveValue('방문객 데이터 활용');
  await expect(page.locator('.rqb-req').filter({ has: tb(page, '마케팅 리드 요구사항 2') }).locator('.rqb-tag--warn')).toHaveText('확인 필요');
  await expect(page.locator('.rqb-sum')).toHaveText('키맨 2 · 요구 5 · 가중치 합 100%');

  // 다시 열면 「작성 중」(보드 RQ_Draft) — 머리 한 줄 · 파일 띠 46
  await page.reload();
  await expect(page.getByRole('heading', { name: '새 요구사항', level: 1 })).toBeVisible();
  await expect(page.locator('.cd-ref')).toHaveText('작성 중');
  await expect(page.locator('.cd-meta')).toHaveText(/^작성 중 · 키맨 2 · 요구 5 · 오늘 \d\d:\d\d 자동 저장 · 저장하면 이 요구사항으로 Storyboard가 만들어져요$/);
  await expect(page.locator('.rqb-drop__t')).toHaveText('파일을 더 놓으면 빈 칸만 채워요 · PPTX · PDF · DOCX · 메일');
  expect(await widths(page)).toEqual(BOARD_W);
  expect([await y(page.locator('.rqb-drop')), await h(page.locator('.rqb-drop'))]).toEqual([196, 46]);
  expect([await y(page.locator('.rqb-ov')), await bottom(page.locator('.rqb-ov'))]).toEqual([254, 878]);
  await page.mouse.move(10, 890);
  await shot(page, 'RQ_Draft');
  const d = await rf(request, id);
  expect([d.ver, d.changes, d.customer, d.sources[0].name]).toEqual([0, 0, 'K 리츠', '회의록_K리츠.txt']);

  // 빈 줄 · 키맨 빼기(카드에 손을 올리면 ×) → 남은 키맨 하나
  await page.locator('[data-keyman]').nth(1).hover();
  await page.getByRole('button', { name: '마케팅 리드 빼기' }).click();
  await expect(page.locator('[data-keyman]')).toHaveCount(1);
  await page.getByRole('button', { name: '빼기 · 시설 원격 관리' }).click();
  await expect.poll(async () => {
    const x = await rf(request, id);
    return [x.keymen.length, x.keymen[0].reqs.map((r: { text: string }) => r.text)];
  }, { timeout: 10_000 }).toEqual([1, ['1층 파사드 미디어로 집객', '테넌트별 콘텐츠 운영']]);
  await expect(page.locator('.rqb-sum')).toHaveText('키맨 1 · 요구 2 · 가중치 합 60%');
});

test('RQ v63 — 빈 새 요구사항 · 아무것도 쓰지 않으면 초안을 만들지 않는다 · 빈 폼 저장 안내 · 1920 폭', async ({ page, request }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const n0 = (await (await request.get('/api/requirements/v1/rq-flows?limit=200')).json()).items.length;
  await page.goto('/requirements/new');
  await expect(page.locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(tb(page, '프로젝트명')).toHaveValue('');
  await expect(page.locator('[data-keyman]')).toHaveCount(1);
  await page.mouse.move(10, 890);
  await shot(page, 'RQ1');
  // 빈 칸을 들어갔다 나와도 · 빈 폼으로 저장을 눌러도 초안이 생기지 않는다
  await tb(page, '프로젝트명').click();
  await tb(page, '고객사').click();
  await page.keyboard.press('Tab');
  await page.getByRole('button', { name: '저장 · Storyboard 만들기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: '프로젝트명 · 고객사 · 요구사항 중 하나는 적어 주세요.' })).toBeVisible();
  await expect(page).toHaveURL(/\/requirements\/new$/);
  // 1920 폭에서도 본문 열은 1180 · 고정 칸 340 · 176 (UI-W-01 · UI-W-04)
  await page.setViewportSize({ width: 1920, height: 1080 });
  expect(await widths(page)).toEqual(BOARD_W);
  expect((await (await request.get('/api/requirements/v1/rq-flows?limit=200')).json()).items.length).toBe(n0);
});

test('RQ v63 — 보드 화면 캡처(RQ_View · RQ1_Edit) · 판이 없는 예전 저장분도 열린다', async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  // 보드 RQBody saved 값(E 자산운용 · 키맨 3 · 요구 8 · 확인 필요 1)
  const keymen = [
    { role: '대표이사', weight: 50, reqs: [{ text: '사용자를 인식하고 반응하는 AI Ready 오피스' }, { text: '최초 AI Ready 공간으로 알리기' }, { text: '에너지 사용량 20% 절감 · 실측 증빙' }] },
    { role: '공간컨텐츠실장', weight: 30, reqs: [{ text: '오피스를 업무환경 플랫폼으로', flag: 'ask' }, { text: '예측 · 반응형 공간' }, { text: '건물 가치 · 임대 선호도 제고' }] },
    { role: '개발사업팀장', weight: 20, reqs: [{ text: 'AI 인프라를 설계 단계에 반영' }, { text: '시공 · 운영 유지보수 부담 최소화' }] },
  ];
  const d = await (await request.post('/api/requirements/v1/rq-flows', { data: { title: '용산 업무시설 재개발 AI Ready 오피스', customer: 'E 자산운용', target: '대표이사', keymen } })).json();
  const fin = await request.post(`/api/requirements/v1/rq-flows/${d.id}:finish`);
  expect(fin.ok(), await fin.text()).toBeTruthy();
  await page.goto(`/requirements/flow/${d.id}`);
  await expect(page.locator('.cd-ref')).toHaveText(`${d.code} v1`);
  await expect(page.locator('.cd-meta')).toHaveText(/ · 키맨 3 · 요구 8 · 확인 필요 1$/);
  await expect(page.locator('.rqb-sum')).toHaveText('키맨 3 · 요구 8 · 가중치 합 100%');
  await expect(tb(page, '프로젝트명')).toHaveClass(/rqb-f--b/);
  await page.mouse.move(10, 890);
  await shot(page, 'RQ_View');

  // 보드 RQ1_Edit: 요구 하나 고침 · 마지막 키맨에 요구 하나 새로 씀 → 고친 곳 2
  await put(tb(page, '대표이사 요구사항 2'), '국내 최초 AI Ready 오피스로 알리기');
  await page.locator('[data-keyman]').nth(2).getByRole('button', { name: '+ 요구사항' }).click();
  await page.keyboard.type('입주 전 시범 운영 공간');
  await page.keyboard.press('Tab');
  await expect(page.locator('.cd-chg')).toHaveText('고친 곳 2', { timeout: 10_000 });
  await expect(page.locator('.rqb-sum')).toHaveText('키맨 3 · 요구 9 · 가중치 합 100%');
  await expect(page.locator('.rqb-tag--chg')).toHaveText(['고침', '새로 씀']);
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await page.mouse.move(10, 890);
  await shot(page, 'RQ1_Edit');
  // 고치다 다른 화면으로 가면 저장할지 묻는다(공용 ContentDetail) — 계속 고치기
  await page.getByRole('link', { name: '고객 요구사항' }).first().click();
  const leave = page.getByRole('dialog', { name: '저장하지 않은 고친 곳' });
  await expect(leave).toBeVisible();
  await expect(leave).toContainText('고친 곳 2개를 아직 저장하지 않았어요');
  await leave.getByRole('button', { name: '계속 고치기' }).click();
  await expect(page).toHaveURL(new RegExp(`/requirements/flow/${d.id}$`));
  await page.getByRole('button', { name: '되돌리기' }).click();
  await expect(page.locator('.cd-chg')).toHaveCount(0);
  await expect(page.locator('[data-keyman]').nth(2).locator('[data-req]')).toHaveCount(2);

  // 판을 남기기 전에 저장한 문서(보드 v58 저장분)도 열리고 고친 곳 0 — 읽을 때 판을 남긴다(API 로 확인)
  const r = await request.post(`/api/requirements/v1/rq-flows/${d.id}:revert`);
  expect(r.status()).toBe(200);
  expect((await r.json()).changes).toBe(0);
  const fresh = await (await request.post('/api/requirements/v1/rq-flows', { data: { title: '판 없음 확인' } })).json();
  const nr = await request.post(`/api/requirements/v1/rq-flows/${fresh.id}:revert`);
  expect(nr.status()).toBe(409);
  expect((await nr.json()).error).toMatchObject({ code: 'NOT_SAVED', message: '아직 저장하지 않아 되돌릴 판이 없어요' });
  await request.delete(`/api/requirements/v1/rq-flows/${fresh.id}`);
});
